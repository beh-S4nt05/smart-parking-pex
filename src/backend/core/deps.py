import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.config import settings
from core.security import decodificar_token
from models.database import get_db
from models.db_models import Usuario

# Define o esquema OAuth2 para extrair token do header Authorization
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)


def get_usuario_logado(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Dependência que obtém o usuário atualmente logado a partir do JWT.
    Usada nas rotas que precisam de autenticação.
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
            detail="Token expirado. Faça login novamente."
        )
    except pyjwt.InvalidTokenError:
        raise credenciais_invalidas

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if usuario is None:
        raise credenciais_invalidas
    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte."
        )

    return usuario
