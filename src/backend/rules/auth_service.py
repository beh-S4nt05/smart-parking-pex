from datetime import timedelta
from typing import Optional

import jwt as pyjwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.security import verificar_senha, criar_hash_senha, criar_token, decodificar_token
from models.db_models import Usuario
from models.schemas import UsuarioCreate, LoginRequest, TokenResponse
from core.config import settings


def criar_usuario(db: Session, dados: UsuarioCreate) -> Usuario:
    """Cria um novo usuário com senha hasheada"""
    usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado no sistema"
        )

    senha_hash = criar_hash_senha(dados.senha)
    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        telefone=dados.telefone,
        placa_veiculo=dados.placa_veiculo,
        senha_hash=senha_hash
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


def autenticar_usuario(db: Session, dados: LoginRequest) -> TokenResponse:
    """Autentica usuário e retorna access + refresh tokens"""
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos"
        )

    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte."
        )

    access_token = criar_token(subject=usuario.id, tipo_token="access")
    refresh_token = criar_token(subject=usuario.id, tipo_token="refresh")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


def renovar_access_token(refresh_token: str) -> dict:
    """
    Renova access token usando um refresh token válido
    Mantendo exatamente o tratamento de erro do seu auth.py original
    """
    try:
        payload = decodificar_token(refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Tipo de token incorreto")

    usuario_id = payload.get("sub")
    novo_access = criar_token(subject=usuario_id, tipo_token="access")

    return {
        "access_token": novo_access,
        "token_type": "bearer"
    }
