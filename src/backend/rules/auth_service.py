import re

import jwt as pyjwt
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.security import (
    criar_hash_senha,
    criar_token,
    decodificar_token,
    verificar_senha,
)
from models.db_models import Usuario
from models.schemas import LoginRequest, TokenResponse, UsuarioCreate, UsuarioResponse


def _somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def buscar_usuario_por_credencial(db: Session, credencial: str) -> Usuario | None:
    """
    Localiza um usuário pelo e-mail OU telefone.
    - Se a credencial contém "@" -> busca por e-mail (case-insensitive).
    - Caso contrário -> compara apenas os dígitos do telefone cadastrado.
    """
    credencial = (credencial or "").strip()
    if not credencial:
        return None

    if "@" in credencial:
        return (
            db.query(Usuario)
            .filter(func.lower(Usuario.email) == credencial.lower())
            .first()
        )

    digitos = _somente_digitos(credencial)
    if len(digitos) < 8:
        return None

    # Escala pequena (demo/piloto): normalizar em Python é mais simples e
    # portável do que SQL de regexp por banco.
    for usuario in db.query(Usuario).filter(Usuario.telefone.isnot(None)).all():
        if _somente_digitos(usuario.telefone) == digitos:
            return usuario
    return None


def criar_usuario(db: Session, dados: UsuarioCreate) -> Usuario:
    """Cria um novo usuário com senha hasheada"""
    email = (dados.email or "").strip().lower()
    usuario_existente = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado no sistema"
        )

    senha_hash = criar_hash_senha(dados.senha)
    novo_usuario = Usuario(
        nome=dados.nome.strip(),
        email=email,
        telefone=_somente_digitos(dados.telefone) if dados.telefone else None,
        placa_veiculo=(dados.placa_veiculo or "").upper().replace(" ", "") or None,
        senha_hash=senha_hash,
        role="usuario",  # Usuários cadastrados publicamente são sempre comuns
        is_ativo=True
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


def montar_token_response(usuario: Usuario, access: str, refresh: str) -> TokenResponse:
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        user=UsuarioResponse.model_validate(usuario),
    )


def autenticar_usuario(db: Session, dados: LoginRequest) -> TokenResponse:
    """
    Autentica usuário por e-mail OU telefone e retorna access + refresh tokens
    + os dados do usuário (o app usa `user` para popular o AuthContext).
    """
    usuario = buscar_usuario_por_credencial(db, dados.email)

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail/telefone ou senha incorretos"
        )

    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte."
        )

    access_token = criar_token(subject=usuario.id, tipo_token="access")
    refresh_token = criar_token(subject=usuario.id, tipo_token="refresh")

    return montar_token_response(usuario, access_token, refresh_token)


def renovar_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """
    Renova o access token usando um refresh token válido e retorna também o
    refresh_token atual (mantido o mesmo para não invalidar outras sessões).
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
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte.",
        )

    # RF-13: o refresh pode estar vivo na assinatura e MORTO em revogação
    # (logout revogou a cadeia; troca de senha marcou o usuário inteiro).
    from core.deps import sessao_revogada

    if sessao_revogada(db, payload, usuario_id):
        raise HTTPException(status_code=401, detail="Sessão encerrada. Faça login novamente.")

    novo_access = criar_token(subject=usuario_id, tipo_token="access")

    return montar_token_response(usuario, novo_access, refresh_token)
