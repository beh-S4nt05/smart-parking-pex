from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.deps import get_usuario_logado
from models.database import get_db
from models.db_models import Usuario
from models.schemas import (
    UsuarioCreate, UsuarioResponse, LoginRequest,
    TokenResponse, RefreshRequest
)
from rules import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


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
