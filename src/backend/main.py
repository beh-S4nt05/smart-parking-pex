import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler

from core.config import settings
from core.security import criar_hash_senha
from core.security_middleware import SecurityHeadersMiddleware
from core.rate_limiter import limiter, rate_limit_exceeded_handler, LIMITS
from core.request_validator import RequestValidationMiddleware
from sqlalchemy.exc import ProgrammingError, IntegrityError
from models.database import engine, Base, SessionLocal
from models.db_models import Usuario, TipoUsuario
from api.api import router as api_router
from api.auth import router as auth_router
from api.admin import router as admin_router

# Cria todas as tabelas no banco de dados automaticamente
try:
    Base.metadata.create_all(bind=engine)
except (ProgrammingError, IntegrityError):
    # Tabelas já existem (corrida entre workers/processos) — segue em frente
    pass

# Cria usuário administrador padrão se não existir (primeira execução)
db = SessionLocal()
admin_existente = (
    db.query(Usuario).filter(Usuario.email == "admin@smartparking.com").first()
)
if not admin_existente:
    admin_padrao = Usuario(
        nome="Administrador",
        email="admin@smartparking.com",
        senha_hash=criar_hash_senha("admin123"),
        role=TipoUsuario.ADMIN,
        is_ativo=True,
    )
    db.add(admin_padrao)
    db.commit()
db.close()

# Inicializa o app do FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    # Em produção desativa completamente /docs e /redoc para não expor documentação
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Adiciona Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(429, rate_limit_exceeded_handler)

# Adiciona middlewares de segurança na ordem correta
# 1. Validador de requisições (bloqueia Postman/navegador e valida assinatura HMAC)
app.add_middleware(RequestValidationMiddleware)

# 2. Middleware de Segurança (SQL Injection, headers, anti duplicação, bloqueio de scanners)
app.add_middleware(SecurityHeadersMiddleware, environment=settings.ENVIRONMENT)

# 2. Middleware de hosts confiáveis (bloqueia acessos com Host header falso em produção)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            # Adicione aqui seu domínio de produção
        ],
    )

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Inclui todos os roteadores
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)


# Rota raiz com limite de acesso
@app.get("/")
async def root():
    return {
        "status": "SmartParking API está rodando perfeitamente!",
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=settings.DEBUG,
        workers=4 if not settings.DEBUG else 1,
    )
