from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.deps import get_usuario_logado
from core.rate_limiter import limiter, LIMITS
from models.database import get_db
from models.db_models import Usuario
from models.schemas import (
    UsuarioCreate, UsuarioResponse, UsuarioMeResponse, LoginRequest,
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
    return await social_auth_service.autenticar_google(dados.id_token, db)


@router.post("/login/facebook", response_model=TokenResponse)
@limiter.limit(LIMITS["login"])
async def login_facebook(request: Request, dados: FacebookLoginRequest, db: Session = Depends(get_db)):
    """
    Login com conta Facebook.
    Envie o access_token obtido após login com o Facebook no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    return await social_auth_service.autenticar_facebook(dados.access_token, db)


@router.post("/login/apple", response_model=TokenResponse)
@limiter.limit(LIMITS["login"])
async def login_apple(request: Request, dados: AppleLoginRequest, db: Session = Depends(get_db)):
    """
    Login com Apple Sign In.
    Envie o identity_token obtido após login com Apple no frontend.
    Cria automaticamente o usuário se ele não existir.
    """
    return await social_auth_service.autenticar_apple(dados.identity_token, db)
