
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.security import decodificar_token
from models.database import get_db
<<<<<<< HEAD
from models.db_models import RevogacaoToken, Usuario, TipoUsuario
=======
from models.db_models import RevogacaoToken, TipoUsuario, Usuario
>>>>>>> eb64687f68d74c589beca0aaf9d41bbce94aeffd


def sessao_revogada(db: Session, payload: dict, usuario_id: str) -> bool:
    """
    RF-13: dois caminhos — jti específico (logout) ou "usuário inteiro desde
    T" (reset de senha/bloqueio). Tokens LEGADOS (sem jti, emitidos antes de
    22/10) só caem no segundo caminho — compatibilidade garantida.
    """
    import datetime as _dt

    iat = payload.get("iat") or 0
    jti = payload.get("jti")
    q = db.query(RevogacaoToken.id)
    if jti:
        achou = q.filter(RevogacaoToken.jti == jti).first()
        if achou:
            return True
    desde = db.query(RevogacaoToken.criado_em).filter(
        RevogacaoToken.usuario_id == usuario_id, RevogacaoToken.jti.is_(None)
    ).first()
    if desde:
        criado = desde[0]
        if criado and criado.tzinfo is not None:
            criado_ts = criado.timestamp()
        else:
<<<<<<< HEAD
            criado_ts = _dt.datetime.replace(criado, tzinfo=_dt.timezone.utc).timestamp() if criado else 0
=======
            criado_ts = _dt.datetime.replace(criado, tzinfo=_dt.UTC).timestamp() if criado else 0
>>>>>>> eb64687f68d74c589beca0aaf9d41bbce94aeffd
        if criado_ts > iat:
            return True
    return False

# Define o esquema OAuth2 para extrair token do header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_usuario_logado(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    """
    Dependência que obtém o usuário atualmente logado a partir do JWT.
    Usada nas rotas que precisam de autenticação de qualquer nível.
    """
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar suas credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decodificar_token(token)
        usuario_id: str = payload.get("sub")
        tipo_token: str = payload.get("type")

        if usuario_id is None or tipo_token != "access":
            raise credenciais_invalidas

    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado. Faça login novamente.",
        )
    except pyjwt.InvalidTokenError:
        raise credenciais_invalidas

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if usuario is None:
        raise credenciais_invalidas
    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte.",
        )

    # RF-13 — o token pode ser válido na assinatura e mesmo assim morto:
    if sessao_revogada(db, payload, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def permissao_necessaria(*cargos_permitidos):
    """
    Dependência genérica para verificar permissões por cargo.
    Uso: permissao_necessaria(TipoUsuario.ADMIN, TipoUsuario.GESTOR)
    """

    def checador(usuario: Usuario = Depends(get_usuario_logado)) -> Usuario:
        if usuario.role not in [c.value for c in cargos_permitidos]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Esta rota requer um dos cargos: {', '.join(cargos_permitidos)}",
            )

        # Se for gestor/financeiro, garante que tem um estacionamento vinculado
        if (
            usuario.role in [TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value]
            and not usuario.estacionamento_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não está vinculado a nenhum estacionamento. Contate o administrador.",
            )

        return usuario

    return checador


def garantir_escopo_estacionamento(
    usuario: Usuario,
    estacionamento_id: str | None,
    acao: str = "usar este estacionamento",
) -> str | None:
    """
    ADR-07 (ACH-06/16): ÚNICA fonte de escopo anti-BOLA para rotas que recebem
    `estacionamento_id` (preços, pagamentos, caixas, cupons, eventos, relatórios).
    - admin: vê/age em qualquer um (ou no global quando id é None);
    - gestor/financeiro: reescrito para o próprio; pedir o dos outros = 403;
    - demais papéis: sem escopo de painel → 403.
    Retorna o id a ser usado (nunca o id alheio).
    """
    role = usuario.role
    if role == TipoUsuario.ADMIN.value:
        return estacionamento_id
    if role not in (TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado. Você não tem permissão para {acao}.",
        )
    if not usuario.estacionamento_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não está vinculado a nenhum estacionamento. Contate o administrador.",
        )
    if estacionamento_id and estacionamento_id != usuario.estacionamento_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado. Você só pode {acao} no seu estacionamento.",
        )
    return usuario.estacionamento_id


# Dependências prontas para usar nas rotas
get_usuario_admin = permissao_necessaria(TipoUsuario.ADMIN)
get_usuario_gestor = permissao_necessaria(TipoUsuario.ADMIN, TipoUsuario.GESTOR)
get_usuario_financeiro = permissao_necessaria(
    TipoUsuario.ADMIN, TipoUsuario.FINANCEIRO, TipoUsuario.GESTOR
)
get_usuario_autenticado = permissao_necessaria(
    TipoUsuario.ADMIN, TipoUsuario.GESTOR, TipoUsuario.FINANCEIRO, TipoUsuario.USUARIO
)
