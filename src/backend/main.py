import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler  # noqa: F401  (mantido p/ compatibilidade)

from core.config import settings
from core.security import criar_hash_senha
from core.security_middleware import SecurityHeadersMiddleware
from core.rate_limiter import limiter, rate_limit_exceeded_handler
from core.request_validator import RequestValidationMiddleware
from sqlalchemy.exc import ProgrammingError, IntegrityError
from models.database import engine, Base, SessionLocal
from models.db_models import Usuario, TipoUsuario, Estacionamento
from api.api import router as api_router
from api.auth import router as auth_router
from api.admin import router as admin_router

# Cria todas as tabelas no banco de dados automaticamente
try:
    Base.metadata.create_all(bind=engine)
except (ProgrammingError, IntegrityError):
    # Tabelas já existem (corrida entre workers/processos) — segue em frente
    pass


def garantir_admin_padrao() -> None:
    """Cria usuário administrador padrão se não existir (primeira execução)"""
    db = SessionLocal()
    try:
        admin_existente = (
            db.query(Usuario).filter(Usuario.email == "admin@smartparking.com").first()
        )
        if not admin_existente:
            admin_padrao = Usuario(
                nome="Administrador",
                email="admin@smartparking.com",
                senha_hash=criar_hash_senha("admin123"),
                role=TipoUsuario.ADMIN.value,
                is_ativo=True,
            )
            db.add(admin_padrao)
            db.commit()
    finally:
        db.close()


def popular_dados_demo() -> None:
    """
    Em desenvolvimento, popula o banco com os shoppings demo de Manaus
    quando ele está vazio — assim `python main.py` já sobe com dados reais
    para o app consumir (a mesma rotina do `seed_demo.py` de linha de comando).
    """
    if not settings.SEED_DEMO_ON_STARTUP or not settings.DEBUG:
        return

    db = SessionLocal()
    try:
        if db.query(Estacionamento).count() > 0:
            return
        from seed_demo import popular_database

        print("🌱 Banco vazio — aplicando seed de demonstração (shoppings de Manaus)...")
        popular_database(db)
    except Exception as exc:  # nunca derruba o servidor por causa do seed
        print(f"⚠️  Seed de demonstração não aplicado: {exc}")
        db.rollback()
    finally:
        db.close()


garantir_admin_padrao()
popular_dados_demo()

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
        # 0.0.0.0 para que o celular (Expo Go) e outros dispositivos da rede
        # consigam alcançar a API — "localhost" só funciona na própria máquina
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
