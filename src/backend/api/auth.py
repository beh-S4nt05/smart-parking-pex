
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.config import settings
from core.deps import get_usuario_logado, oauth2_scheme
from core.rate_limiter import LIMITS, limiter
from models.database import get_db
from models.db_models import CredencialEstacionamento, Reserva, StatusReserva, Usuario, Veiculo
from models.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UsuarioCreate,
    UsuarioMeResponse,
    UsuarioResponse,
    VeiculoCadastro,
    validar_tamanho_senha,
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
    is_pcd: bool | None = None  # legado; credenciais oficiais usam processo separado
    data_nascimento: date | None = None

    def _limpa(self):
        if self.placa_veiculo:
            self.placa_veiculo = self.placa_veiculo.upper().strip()
        return self


class TrocarSenha(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=6, max_length=72)

    @field_validator("nova_senha")
    @classmethod
    def nova_senha_compativel_com_bcrypt(cls, senha: str) -> str:
        return validar_tamanho_senha(senha)


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
            expira_em=_dt.datetime.fromtimestamp(exp, _dt.timezone.utc) if exp else None,
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
    if muda.get("data_nascimento") and muda["data_nascimento"] > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=422, detail="Data de nascimento não pode estar no futuro")
    for campo, val in muda.items():
        if isinstance(val, (bool, date)) or val is None:  # is_pcd não passa pelo strip de strings
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


# --- Garagem do motorista e pedidos de credenciais especiais (V1) ---
class VeiculoResponse(BaseModel):
    id: str
    placa: str
    categoria: str
    motorizacao: str
    modelo: str | None
    principal: bool
    ativo: bool

    model_config = {"from_attributes": True}


class CredencialResponse(BaseModel):
    id: str
    tipo: str
    status: str
    validade: date | None = None

    model_config = {"from_attributes": True}


class PedidoCredencial(BaseModel):
    tipo: Literal["idoso", "pcd"]


def _veiculo_do_usuario(db: Session, usuario_id: str, veiculo_id: str) -> Veiculo:
    """Evita exposição ou modificação de veículo de outra conta."""
    veiculo = db.query(Veiculo).filter(
        Veiculo.id == veiculo_id,
        Veiculo.usuario_id == usuario_id,
        Veiculo.ativo.is_(True),
    ).first()
    if veiculo is None:
        raise HTTPException(status_code=404, detail="Veículo não encontrado nesta conta")
    return veiculo


def _bloquear_usuario(db: Session, usuario_id: str) -> Usuario:
    # Serializa as escolhas de veículo principal (e o cadastro do primeiro)
    # no PostgreSQL, evitando duas escolhas concorrentes de principal.
    return db.query(Usuario).filter(Usuario.id == usuario_id).with_for_update().one()


def _reservas_ativas_do_veiculo(db: Session, veiculo_id: str) -> bool:
    return db.query(Reserva.id).filter(
        Reserva.veiculo_id == veiculo_id,
        Reserva.status == StatusReserva.CONFIRMADA,
    ).first() is not None


def _fixar_principal(db: Session, usuario: Usuario, escolhido: Veiculo) -> None:
    # O projeto configura autoflush=False. Persistir alterações pendentes
    # antes de consultar veículos ativos/principal na mesma transação.
    db.flush()
    for veiculo in db.query(Veiculo).filter(
        Veiculo.usuario_id == usuario.id, Veiculo.ativo.is_(True)
    ).all():
        veiculo.principal = veiculo.id == escolhido.id
    usuario.placa_veiculo = escolhido.placa


@router.get("/veiculos", response_model=list[VeiculoResponse])
def listar_veiculos(usuario: Usuario = Depends(get_usuario_logado), db: Session = Depends(get_db)):
    return db.query(Veiculo).filter(
        Veiculo.usuario_id == usuario.id, Veiculo.ativo.is_(True)
    ).order_by(Veiculo.principal.desc(), Veiculo.criado_em.asc(), Veiculo.id.asc()).all()


@router.post("/veiculos", response_model=VeiculoResponse, status_code=201)
def cadastrar_veiculo(
    dados: VeiculoCadastro,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    dono = _bloquear_usuario(db, usuario.id)
    duplicado = db.query(Veiculo).filter(
        Veiculo.usuario_id == usuario.id, Veiculo.placa == dados.placa
    ).first()
    if duplicado and duplicado.ativo:
        raise HTTPException(status_code=409, detail="Placa já cadastrada nesta conta")

    if duplicado:
        # Restaura um veículo previamente desativado, respeitando a unique key.
        # Uma reserva ativa nunca pode apontar para um veículo desativado,
        # mas bloqueamos o caso por segurança em bancos legados.
        if _reservas_ativas_do_veiculo(db, duplicado.id):
            raise HTTPException(status_code=409, detail="Veículo vinculado a uma reserva ativa")
        duplicado.ativo = True
        duplicado.categoria = dados.categoria
        duplicado.motorizacao = dados.motorizacao
        duplicado.modelo = dados.modelo
        duplicado.principal = False
        veiculo = duplicado
    else:
        veiculo = Veiculo(
            usuario_id=usuario.id, placa=dados.placa,
            categoria=dados.categoria, motorizacao=dados.motorizacao,
            modelo=dados.modelo, principal=False,
        )
        db.add(veiculo)
        db.flush()

    principal = db.query(Veiculo).filter(
        Veiculo.usuario_id == usuario.id,
        Veiculo.ativo.is_(True),
        Veiculo.principal.is_(True),
    ).first()
    if principal is None:
        _fixar_principal(db, dono, veiculo)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.put("/veiculos/{veiculo_id}", response_model=VeiculoResponse)
def atualizar_veiculo(
    veiculo_id: str,
    dados: VeiculoCadastro,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    dono = _bloquear_usuario(db, usuario.id)
    veiculo = _veiculo_do_usuario(db, usuario.id, veiculo_id)
    existe = db.query(Veiculo).filter(
        Veiculo.usuario_id == usuario.id, Veiculo.placa == dados.placa,
        Veiculo.id != veiculo_id,
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="Placa já cadastrada nesta conta")
    alteracao_operacional = (
        veiculo.placa != dados.placa
        or veiculo.categoria != dados.categoria
        or veiculo.motorizacao != dados.motorizacao
    )
    if alteracao_operacional and _reservas_ativas_do_veiculo(db, veiculo.id):
        raise HTTPException(
            status_code=409,
            detail="Há uma reserva ativa com este veículo. Cancele ou conclua a reserva antes de mudar placa, tipo ou motorização.",
        )
    veiculo.placa = dados.placa
    veiculo.categoria = dados.categoria
    veiculo.motorizacao = dados.motorizacao
    veiculo.modelo = dados.modelo
    if veiculo.principal:
        dono.placa_veiculo = veiculo.placa
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.put("/veiculos/{veiculo_id}/principal", response_model=VeiculoResponse)
def definir_principal(
    veiculo_id: str,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    dono = _bloquear_usuario(db, usuario.id)
    veiculo = _veiculo_do_usuario(db, usuario.id, veiculo_id)
    _fixar_principal(db, dono, veiculo)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.delete("/veiculos/{veiculo_id}", status_code=204)
def remover_veiculo(
    veiculo_id: str,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    dono = _bloquear_usuario(db, usuario.id)
    veiculo = _veiculo_do_usuario(db, usuario.id, veiculo_id)
    if _reservas_ativas_do_veiculo(db, veiculo.id):
        raise HTTPException(
            status_code=409,
            detail="Veículo vinculado a uma reserva ativa. Cancele ou conclua a reserva antes de removê-lo.",
        )
    era_principal = veiculo.principal
    veiculo.principal = False
    veiculo.ativo = False  # remoção lógica: preserva vínculos históricos
    db.flush()  # SessionLocal.autoflush=False: não selecionar o removido como sucessor
    if era_principal:
        proximo = db.query(Veiculo).filter(
            Veiculo.usuario_id == usuario.id, Veiculo.ativo.is_(True)
        ).order_by(Veiculo.criado_em.asc(), Veiculo.id.asc()).first()
        if proximo:
            _fixar_principal(db, dono, proximo)
        else:
            dono.placa_veiculo = None
    db.commit()


def _expirar_credenciais_vencidas(db: Session, usuario_id: str) -> None:
    """Não exibir credencial vencida como aprovada; permitir nova solicitação."""
    hoje = datetime.now(timezone.utc).date()
    vencidas = db.query(CredencialEstacionamento).filter(
        CredencialEstacionamento.usuario_id == usuario_id,
        CredencialEstacionamento.status == "aprovado",
        CredencialEstacionamento.validade.isnot(None),
        CredencialEstacionamento.validade < hoje,
    ).all()
    for cred in vencidas:
        cred.status = "expirado"
    if vencidas:
        db.commit()


@router.get("/credenciais", response_model=list[CredencialResponse])
def listar_credenciais(usuario: Usuario = Depends(get_usuario_logado), db: Session = Depends(get_db)):
    _expirar_credenciais_vencidas(db, usuario.id)
    return db.query(CredencialEstacionamento).filter(CredencialEstacionamento.usuario_id == usuario.id).all()


@router.post("/credenciais/solicitar", response_model=CredencialResponse, status_code=201)
def solicitar_credencial(
    dados: PedidoCredencial, usuario: Usuario = Depends(get_usuario_logado), db: Session = Depends(get_db)
):
    _expirar_credenciais_vencidas(db, usuario.id)
    if dados.tipo == "idoso":
        nascimento = usuario.data_nascimento
        if nascimento is None:
            raise HTTPException(status_code=422, detail="Informe a data de nascimento no perfil")
        hoje = datetime.now(timezone.utc).date()
        idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        if idade < 60:
            raise HTTPException(status_code=422, detail="Credencial de idoso exige 60 anos ou mais")
    ja = db.query(CredencialEstacionamento).filter(
        CredencialEstacionamento.usuario_id == usuario.id,
        CredencialEstacionamento.tipo == dados.tipo,
        CredencialEstacionamento.status.in_(["pendente", "aprovado"]),
    ).first()
    if ja:
        raise HTTPException(status_code=409, detail="Já existe uma solicitação ou credencial válida")
    cred = CredencialEstacionamento(usuario_id=usuario.id, tipo=dados.tipo, status="pendente")
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


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


# --- Identidade V1 (PR60). E-mail depende de servidor SMTP configurado. ---
class EmailIdentidade(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class TokenIdentidadeIn(BaseModel):
    token: str = Field(min_length=24, max_length=128)


class RedefinirSenhaIn(TokenIdentidadeIn):
    nova_senha: str = Field(min_length=6, max_length=72)

    @field_validator("nova_senha")
    @classmethod
    def validar_senha(cls, senha: str) -> str:
        return validar_tamanho_senha(senha)


class MFAIniciarIn(BaseModel):
    senha_atual: str


class MFAConfirmarIn(BaseModel):
    codigo: str = Field(pattern=r"^[0-9]{6}$")


@router.post("/email/solicitar", status_code=202)
@limiter.limit(LIMITS["registro"])
def solicitar_verificacao_email(request: Request, dados: EmailIdentidade, db: Session = Depends(get_db)):
    from rules.identity_service import solicitar_desafio
    solicitar_desafio(db, dados.email, "verificar_email")
    return {"mensagem": "Se a conta existir e estiver pendente, a mensagem será enviada."}


@router.post("/email/confirmar", status_code=204)
@limiter.limit(LIMITS["auth_escrita"])
def confirmar_verificacao_email(request: Request, dados: TokenIdentidadeIn, db: Session = Depends(get_db)):
    from rules.identity_service import confirmar_email
    confirmar_email(db, dados.token)


@router.post("/senha/esqueci", status_code=202)
@limiter.limit(LIMITS["registro"])
def solicitar_recuperacao(request: Request, dados: EmailIdentidade, db: Session = Depends(get_db)):
    from rules.identity_service import solicitar_desafio
    solicitar_desafio(db, dados.email, "recuperar_senha")
    return {"mensagem": "Se a conta existir, serão enviadas instruções."}


@router.post("/senha/redefinir", status_code=204)
@limiter.limit(LIMITS["auth_escrita"])
def recuperar_senha(request: Request, dados: RedefinirSenhaIn, db: Session = Depends(get_db)):
    from rules.identity_service import redefinir_senha
    redefinir_senha(db, dados.token, dados.nova_senha)


@router.post("/mfa/iniciar")
@limiter.limit(LIMITS["auth_escrita"])
def iniciar_mfa(
    request: Request, dados: MFAIniciarIn, db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    from rules.identity_service import iniciar_mfa as _iniciar
    return _iniciar(db, usuario, dados.senha_atual)


@router.post("/mfa/confirmar", status_code=204)
@limiter.limit(LIMITS["auth_escrita"])
def confirmar_mfa(
    request: Request, dados: MFAConfirmarIn, db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    from rules.identity_service import confirmar_mfa as _confirmar
    _confirmar(db, usuario, dados.codigo)
