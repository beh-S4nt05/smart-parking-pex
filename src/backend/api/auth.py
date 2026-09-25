from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.deps import get_usuario_logado
from models.database import get_db
from models.db_models import Usuario
from models.schemas import (
    UsuarioCreate, UsuarioResponse, LoginRequest,
    TokenResponse, RefreshRequest
)
from rules import auth_service, social_auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


# Schemas para login social
class GoogleLoginRequest(BaseModel):
    id_token: str


class FacebookLoginRequest(BaseModel):
    access_token: str


class AppleLoginRequest(BaseModel):
    identity_token: str
    nome: Optional[str] = None


@router.post("/registrar", response_model=UsuarioResponse, status_code=201)
async def registrar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    """Endpoint para cadastro de novo usuário"""
    return auth_service.criar_usuario(db, dados)


@router.post("/login", response_model=TokenResponse)
async def login(dados: LoginRequest, db: Session = Depends(get_db)):
    """Endpoint de login: retorna access_token e refresh_token"""
    return auth_service.autenticar_usuario(db, dados)


@router.post("/refresh")
async def refresh_token(dados: RefreshRequest):
    """
    Endpoint para renovar access_token usando refresh_token
    Com tratamento de erro exatamente como no seu auth.py original
    """
    return auth_service.renovar_access_token(dados.refresh_token)


@router.get("/me", response_model=UsuarioResponse)
async def obter_dados_usuario_logado(usuario: Usuario = Depends(get_usuario_logado)):
    """Retorna dados do usuário atualmente logado (requer token JWT)"""
    return usuario


# --- Rotas de Autenticação Social (OAuth) ---
@router.post("/login/google", response_model=TokenResponse)
async def login_google(dados: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Login com conta Google.
    Envie o id_token obtido após login com o Google no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    return await social_auth_service.autenticar_google(dados.id_token, db)


@router.post("/login/facebook", response_model=TokenResponse)
async def login_facebook(dados: FacebookLoginRequest, db: Session = Depends(get_db)):
    """
    Login com conta Facebook.
    Envie o access_token obtido após login com o Facebook no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    return await social_auth_service.autenticar_facebook(dados.access_token, db)


@router.post("/login/apple", response_model=TokenResponse)
async def login_apple(dados: AppleLoginRequest, db: Session = Depends(get_db)):
    """
    Login com Apple Sign In.
    Envie o identity_token obtido após login com Apple no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    return await social_auth_service.autenticar_apple(dados.identity_token, db)
