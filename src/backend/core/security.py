import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from core.config import settings


MAX_SENHA_BYTES = 72  # limite criptográfico do bcrypt, não apenas contagem de caracteres


def senha_cabe_no_bcrypt(senha: str) -> bool:
    return len(senha.encode("utf-8")) <= MAX_SENHA_BYTES


def criar_hash_senha(senha: str) -> str:
    """Gera hash bcrypt sem truncamento silencioso ou exceção em entrada longa."""
    if not senha_cabe_no_bcrypt(senha):
        raise ValueError("A senha excede o limite de 72 bytes do bcrypt")
    senha_bytes = senha.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha_bytes, salt).decode("utf-8")


def verificar_senha(senha_limpa: str, senha_hash: str) -> bool:
    """Entrada longa ou hash corrompido falha fechado, sem derrubar o login."""
    if not senha_cabe_no_bcrypt(senha_limpa):
        return False
    try:
        return bcrypt.checkpw(senha_limpa.encode("utf-8"), senha_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def criar_token(
    subject: str | Any,
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
        # RF-13: jti permite revogar UM token específico no logout
        "jti": uuid.uuid4().hex,
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
