
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import settings
from core.deps import get_usuario_logado, oauth2_scheme
from core.rate_limiter import LIMITS, limiter
from models.database import get_db
from models.db_models import Usuario
from models.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UsuarioCreate,
    UsuarioMeResponse,
    UsuarioResponse,
)
from rules import auth_service, social_auth_service


def _social_habilitado() -> None:
    """ACH-08/ADR-06: Google/Apple/Facebook têm bugs conhecidos (JWKS/Facebook
    sem app validation) e o front não os usa em produção — as rotas ficam
    atrás de flag; desligadas, respondem 404."""
    if not settings.LOGIN_SOCIAL_ENABLED:
        raise HTTPException(
            status_code=404,
            detail="Login social desabilitado (LOGIN_SOCIAL_ENABLED=false)",
        )

router = APIRouter(prefix="/auth", tags=["Autenticação"])


# Schemas para login social
class GoogleLoginRequest(BaseModel):
    id_token: str


class FacebookLoginRequest(BaseModel):
    access_token: str


class AppleLoginRequest(BaseModel):
    identity_token: str
    nome: str | None = None


@router.post("/registrar", response_model=UsuarioResponse, status_code=201)
@limiter.limit(LIMITS["registro"])
async def registrar_usuario(
    request: Request, dados: UsuarioCreate, db: Session = Depends(get_db)
):
    """Endpoint para cadastro de novo usuário"""
    return auth_service.criar_usuario(db, dados)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LIMITS["login"])
async def login(request: Request, dados: LoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint de login (e-mail OU telefone + senha).
    Retorna access_token, refresh_token e os dados do usuário autenticado.
    """
    return auth_service.autenticar_usuario(db, dados)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(LIMITS["refresh"])
async def refresh_token(request: Request, dados: RefreshRequest, db: Session = Depends(get_db)):
    """
    Endpoint para renovar access_token usando refresh_token.
    Também retorna o usuário atualizado, para o app manter o estado coerente.
    """
    return auth_service.renovar_access_token(db, dados.refresh_token)


class UsuarioAtualizar(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=120)
    telefone: str | None = Field(None, max_length=20)
    placa_veiculo: str | None = Field(None, max_length=12)
    is_pcd: bool | None = None  # RF-47: declarar/revogar depois também

    def _limpa(self):
        if self.placa_veiculo:
            self.placa_veiculo = self.placa_veiculo.upper().strip()
        return self


class TrocarSenha(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=6, max_length=72)


@router.post("/logout", status_code=204)
@limiter.limit(LIMITS["auth_escrita"])
def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    refresh_token: str | None = None,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    """
    RF-13: encerra a sessão no SERVIDOR — o access token atual (jti) entra na
    lista de revogação e para de ser aceito em qualquer rota, mesmo antes do
    `exp`. O refresh token (query `?refresh_token=`) também é revogado,
    quebrando a cadeia de renovação silenciosa. Tokens antigos emitidos antes
    de 22/10 (sem jti) sobrevivem até o `exp` — documentado no SDD.
    """
    from core.security import decodificar_token as _dec
    from core.timeutils import utc_agora
    from models.db_models import RevogacaoToken

    agora = utc_agora()
    def _revogar(tok: str, motivo: str):
        try:
            pl = _dec(tok)
        except Exception:
            return
        jti = pl.get("jti")
        if not jti:
            return
        import datetime as _dt
        exp = pl.get("exp")
        db.add(RevogacaoToken(
            jti=jti, motivo=motivo, criado_em=agora,
            expira_em=_dt.datetime.fromtimestamp(exp, _dt.UTC) if exp else None,
        ))

    _revogar(token, "logout")
    if refresh_token:
        _revogar(refresh_token, "logout_refresh")
    # faxina: linhas já vencidas não servem mais para nada
    db.query(RevogacaoToken).filter(
        RevogacaoToken.expira_em.isnot(None), RevogacaoToken.expira_em < agora
    ).delete(synchronize_session=False)
    db.commit()


@router.put("/me", response_model=UsuarioMeResponse)
@limiter.limit(LIMITS["auth_escrita"])
def atualizar_perfil(
    request: Request,
    dados: UsuarioAtualizar,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    """RF-15: o próprio usuário edita nome/telefone/placa (e-mail não é editável)."""
    muda = dados._limpa().model_dump(exclude_unset=True)  # _limpa: placa → upper
    if not muda:
        raise HTTPException(status_code=422, detail="Nada para atualizar")
    if "nome" in muda and (muda["nome"] or "").strip().__len__() < 2:
        raise HTTPException(status_code=422, detail="Nome precisa de 2+ caracteres")
    for campo, val in muda.items():
        if isinstance(val, bool):  # is_pcd não passa pelo strip de strings
            setattr(usuario, campo, val)
        else:
            setattr(usuario, campo, (val or "").strip() or None)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/senha", status_code=204)
@limiter.limit(LIMITS["auth_escrita"])
def trocar_senha(
    request: Request,
    dados: TrocarSenha,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    """
    RF-15: troca de senha com a senha atual — e, ao contrário, derruba TODAS
    as outras sessões do usuário (marcação de revogação global): quem troca a
    senha quer estar sozinho no sistema de novo.
    """
    from core.security import criar_hash_senha, verificar_senha
    from core.timeutils import utc_agora
    from models.db_models import RevogacaoToken

    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Senha atual incorreta")
    if dados.senha_atual == dados.nova_senha:
        raise HTTPException(status_code=422, detail="A nova senha não pode ser igual à atual")
    usuario.senha_hash = criar_hash_senha(dados.nova_senha)
    # Marca global: todos os tokens emitidos antes de agora caem — inclusive o
    # desta chamada (já validada: o 204 sai; o próximo request dá 401 e o app
    # faz re-login sozinho com a senha nova). Padrão "mudei a senha, religue".
    db.add(RevogacaoToken(jti=None, usuario_id=usuario.id, motivo="troca_senha",
                          criado_em=utc_agora()))
    db.commit()


@router.get("/me", response_model=UsuarioMeResponse)
async def obter_dados_usuario_logado(
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    """Retorna dados do usuário atualmente logado + estacionamento vinculado"""
    from models.db_models import Estacionamento

    payload = UsuarioMeResponse.model_validate(usuario)
    if usuario.estacionamento_id:
        est = (
            db.query(Estacionamento)
            .filter(Estacionamento.id == usuario.estacionamento_id)
            .first()
        )
        if est:
            payload.estacionamento_nome = est.nome
    return payload


# --- Rotas de Autenticação Social (OAuth) ---
@router.post("/login/google", response_model=TokenResponse)
@limiter.limit(LIMITS["login"])
async def login_google(request: Request, dados: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Login com conta Google.
    Envie o id_token obtido após login com o Google no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    _social_habilitado()
    return await social_auth_service.autenticar_google(dados.id_token, db)


@router.post("/login/facebook", response_model=TokenResponse)
@limiter.limit(LIMITS["login"])
async def login_facebook(request: Request, dados: FacebookLoginRequest, db: Session = Depends(get_db)):
    """
    Login com conta Facebook.
    Envie o access_token obtido após login com o Facebook no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    _social_habilitado()
    return await social_auth_service.autenticar_facebook(dados.access_token, db)


@router.post("/login/apple", response_model=TokenResponse)
@limiter.limit(LIMITS["login"])
async def login_apple(request: Request, dados: AppleLoginRequest, db: Session = Depends(get_db)):
    """
    Login com Apple Sign In.
    Envie o identity_token obtido após login com Apple no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    _social_habilitado()
    return await social_auth_service.autenticar_apple(dados.identity_token, db)
