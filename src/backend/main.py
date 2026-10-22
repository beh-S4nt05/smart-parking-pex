import asyncio
import contextlib
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler  # noqa: F401  (mantido p/ compatibilidade)
from sqlalchemy.exc import IntegrityError, ProgrammingError

from api.admin import router as admin_router
from api.api import router as api_router
from api.auth import router as auth_router
<<<<<<< HEAD
from api.admin import router as admin_router
from api.sensores import router as sensores_router
=======
from api.sensores import router as sensores_router
from core.config import settings
from core.rate_limiter import limiter, rate_limit_exceeded_handler
from core.request_validator import RequestValidationMiddleware
from core.security import criar_hash_senha
from core.security_middleware import SecurityHeadersMiddleware
from models.database import Base, SessionLocal, engine
from models.db_models import Estacionamento, TipoUsuario, Usuario
>>>>>>> eb64687f68d74c589beca0aaf9d41bbce94aeffd

# Cria todas as tabelas no banco de dados automaticamente
with contextlib.suppress(ProgrammingError, IntegrityError):
    # Tabelas já existem (corrida entre workers/processos) — segue em frente
    Base.metadata.create_all(bind=engine)


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


# ACH-02 (M2-02): em PRODUÇÃO o admin padrão NÃO nasce com senha sabida —
# crie via `python -c "..."`/script interno ou defina DEMO_ADMIN_FIXTURE.
if settings.ENVIRONMENT.lower() == "production":
    print("🔒 production: admin padrão e seed demo desabilitados")
else:
    garantir_admin_padrao()
    popular_dados_demo()

async def _zapeador_reservas() -> None:
    """
    RF-23: a cada 60 s expira reservas CONFIRMADA vencidas e libera as vagas
    presas a elas. O mesmo zap é chamado sob demanda nas leituras do app
    (idempotente), então este loop é só a rede de segurança do mapa/painel.
    """
    from rules import reserva_service

    while True:
        try:
            await asyncio.sleep(60)
            db = SessionLocal()
            try:
                n = reserva_service.expirar_reservas_vencidas(db)
                if n:
                    print(f"⏱️  {n} reserva(s) expirada(s) — vagas liberadas")
            finally:
                db.close()
        except asyncio.CancelledError:  # noqa: PERF203 - zapador: try/except no laco e o desenho (poll 15s)
            raise
        except Exception as exc:
            print(f"⚠️  zapador de reservas: {exc}")
            await asyncio.sleep(10)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    task = asyncio.create_task(_zapeador_reservas())
    try:
        yield
    finally:
        task.cancel()


# Inicializa o app do FastAPI
app = FastAPI(
    lifespan=_lifespan,
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
# ACH-04: o handler precisa estar preso à EXCEÇÃO do slowapi — mapear só o
# status 429 deixava o RateLimitExceeded virar 500 antes de chegar nele.
from slowapi.errors import RateLimitExceeded

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(429, rate_limit_exceeded_handler)

# Adiciona middlewares de segurança na ordem correta
# 1. Validador de requisições (bloqueia Postman/navegador e valida assinatura HMAC)
app.add_middleware(RequestValidationMiddleware)

# 2. Middleware de Segurança (SQL Injection, headers, anti duplicação, bloqueio de scanners)
app.add_middleware(SecurityHeadersMiddleware, environment=settings.ENVIRONMENT)

# 2. Middleware de hosts confiáveis (bloqueia acessos com Host header falso em produção)
# A lista vem de TRUSTED_HOSTS (config/.env) — mantida hardcoded só para localhost,
# o acesso via Nginx ou IP da LAN levava "400 Invalid host header" e o app
# parecia caído para quem não estivesse na máquina do servidor.
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS,
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
app.include_router(sensores_router, prefix="/api")


# Rota raiz com limite de acesso
@app.get("/")
async def root():
    return {
        "status": "SmartParking API está rodando perfeitamente!",
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Infra"])
async def health():
    """Ping barato de infraestrutura: healthcheck do Docker (compose), balanceamento
    do Nginx e smoke test dos dias de apresentação (scripts/smoke_mvp.sh).
    É GET e não modifica nada — funciona em qualquer ENVIRONMENT."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import socket

    def _ip_lan() -> str:
        """Descobre o IP desta máquina na rede local (para o celular alcançar a API)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except OSError:
            return "127.0.0.1"

    ip_lan = _ip_lan()

    print("─" * 60)
    print(f"🌐 SmartParking API — porta {settings.PORT}")
    print(f"   neste computador   : http://localhost:{settings.PORT}/docs")
    print(f"   celular / outra rede: http://{ip_lan}:{settings.PORT}")
    print(f'   no app, use no .env : EXPO_PUBLIC_API_URL="http://{ip_lan}:{settings.PORT}"')
    print("   porta ocupada?       → PORT=8010 no src/backend/.env (e ajuste o .env do front)")
    print("─" * 60)

    uvicorn.run(
        "main:app",
        # 0.0.0.0 para que o celular (Expo Go) e outros dispositivos da rede
        # consigam alcançar a API — "localhost" só funciona na própria máquina
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
