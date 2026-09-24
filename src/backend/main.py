import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from models.database import engine, Base
from api.api import router as api_router
from api.auth import router as auth_router


# Cria todas as tabelas no banco de dados automaticamente
# Em produção recomenda-se usar Alembic para migrações, mas para desenvolvimento isso funciona
Base.metadata.create_all(bind=engine)

# Inicializa o app do FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui todos os roteadores
app.include_router(api_router)
app.include_router(auth_router)


# Rota raiz
@app.get("/")
async def root():
    return {
        "status": "SmartParking API está rodando perfeitamente!",
        "docs": "/docs",
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
