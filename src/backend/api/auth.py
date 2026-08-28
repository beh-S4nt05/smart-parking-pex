from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/auth", tags=["Autenticação"])

SECRET_KEY = (
    "sua_chave_secreta_de_producao_aqui"  # Idealmente via variável de ambiente [22, 23]
)
ALGORITHM = "HS256"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    try:
        payload = jwt.decode(
            body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
        )  # Importante usar "algorithms" no plural [22, 24]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Tipo de token incorreto")

    # Gera novo access_token de curta duração (ex: 15 minutos) [22, 23]
    now = datetime.now(timezone.utc)
    new_access_payload = {
        "sub": payload["sub"],
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    return {
        "access_token": jwt.encode(new_access_payload, SECRET_KEY, algorithm=ALGORITHM),
        "token_type": "bearer",
    }
