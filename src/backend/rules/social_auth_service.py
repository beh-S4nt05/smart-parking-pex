from typing import Optional
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.security import criar_token
from models.db_models import Usuario, TipoUsuario
from models.schemas import TokenResponse


async def autenticar_google(token_id: str, db: Session) -> TokenResponse:
    """
    Autentica usuário com Google ID Token.
    Frontend obtém o token após login com Google e envia para aqui.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Login com Google não configurado no backend"
        )

    # Valida o token com a API do Google
    async with httpx.AsyncClient() as client:
        try:
            resposta = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": token_id},
                timeout=10
            )
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Falha ao validar token do Google"
            )

        if resposta.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Token do Google inválido ou expirado"
            )

        dados_usuario = resposta.json()

        if dados_usuario.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=401,
                detail="Token do Google não pertence a esta aplicação"
            )

    email = dados_usuario.get("email")
    nome = dados_usuario.get("name", "")
    foto = dados_usuario.get("picture")
    email_verificado = dados_usuario.get("email_verified", False)

    if not email or not email_verificado:
        raise HTTPException(
            status_code=401,
            detail="E-mail não verificado no Google"
        )

    return _processar_login_social(db, email=email, nome=nome, foto_url=foto)


async def autenticar_facebook(access_token: str, db: Session) -> TokenResponse:
    """
    Autentica usuário com Facebook Access Token.
    Frontend envia o access token obtido após login com Facebook.
    """
    if not settings.FACEBOOK_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Login com Facebook não configurado no backend"
        )

    async with httpx.AsyncClient() as client:
        try:
            resposta = await client.get(
                "https://graph.facebook.com/me",
                params={
                    "fields": "id,name,email,picture",
                    "access_token": access_token
                },
                timeout=10
            )
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Falha ao validar token do Facebook"
            )

        if resposta.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Token do Facebook inválido ou expirado"
            )

        dados_usuario = resposta.json()

    email = dados_usuario.get("email")
    nome = dados_usuario.get("name", "")
    foto = dados_usuario.get("picture", {}).get("data", {}).get("url")

    if not email:
        raise HTTPException(
            status_code=401,
            detail="É necessário dar permissão de e-mail para login com Facebook"
        )

    return _processar_login_social(db, email=email, nome=nome, foto_url=foto)


async def autenticar_apple(identity_token: str, db: Session) -> TokenResponse:
    """
    Autentica usuário com Apple Sign In ID Token.
    Frontend envia o identity token obtido após login com Apple.
    """
    # Apple usa JWT como token ID, podemos validar o público e assinatura
    import jwt as pyjwt
    try:
        # Primeiro pega as chaves públicas da Apple
        async with httpx.AsyncClient() as client:
            chaves = await client.get("https://appleid.apple.com/auth/keys", timeout=10)
            chaves_json = chaves.json()

        payload = pyjwt.decode(
            identity_token,
            chaves_json,
            audience=settings.APPLE_CLIENT_ID,
            algorithms=["RS256"],
            options={"verify_exp": True}
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token da Apple inválido ou expirado"
        )

    email = payload.get("email")
    nome = payload.get("name", "Usuário Apple")
    if not email:
        raise HTTPException(
            status_code=401,
            detail="E-mail não retornado pela Apple"
        )

    return _processar_login_social(db, email=email, nome=nome)


def _processar_login_social(db: Session, email: str, nome: str, foto_url: Optional[str] = None) -> TokenResponse:
    """
    Função interna compartilhada por todos os provedores OAuth:
    1. Verifica se o e-mail já existe → se sim, loga o usuário
    2. Se não existir, cria um novo usuário automaticamente
    3. Retorna os tokens de acesso como no login normal
    """
    # Busca usuário por e-mail
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario:
        # Cria novo usuário automaticamente para login social
        # Gera uma senha aleatória segura (não vai ser usada para login)
        import secrets
        senha_aleatoria = secrets.token_urlsafe(32)
        from core.security import criar_hash_senha

        usuario = Usuario(
            nome=nome.strip() if nome else email.split("@")[0],
            email=email,
            senha_hash=criar_hash_senha(senha_aleatoria),
            role=TipoUsuario.USUARIO,
            is_ativo=True
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte."
        )

    # Gera tokens igual no login normal
    access_token = criar_token(subject=usuario.id, tipo_token="access")
    refresh_token = criar_token(subject=usuario.id, tipo_token="refresh")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )
