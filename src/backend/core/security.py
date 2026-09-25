from datetime import datetime, timedelta, timezone
from typing import Any, Union

import jwt
import bcrypt

from core.config import settings


def criar_hash_senha(senha: str) -> str:
    """Gera hash seguro para senhas de usuário usando bcrypt diretamente"""
    senha_bytes = senha.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha_bytes, salt).decode("utf-8")


def verificar_senha(senha_limpa: str, senha_hash: str) -> bool:
    """Verifica se uma senha limpa corresponde ao hash armazenado"""
    senha_bytes = senha_limpa.encode("utf-8")
    hash_bytes = senha_hash.encode("utf-8")
    return bcrypt.checkpw(senha_bytes, hash_bytes)


def criar_token(
    subject: Union[str, Any],
    tipo_token: str,
    expiracao_delta: timedelta | None = None
) -> str:
    """
    Cria um JWT token (access ou refresh)
    Implementação igual ao seu auth.py original, porém desacoplada
    """
    now = datetime.now(timezone.utc)

    if expiracao_delta:
        expira = now + expiracao_delta
    else:
        if tipo_token == "access":
            expira = now + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        else:  # refresh
            expira = now + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )

    payload = {
        "sub": str(subject),
        "type": tipo_token,
        "iat": now,
        "exp": expira,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict[str, Any]:
    """
    Decodifica e valida um JWT token, lançando erro se inválido
    Mantendo o uso do plural em algorithms como no seu código original
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
