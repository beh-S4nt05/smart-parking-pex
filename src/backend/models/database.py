from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

# 🔧 Fonte ÚNICA de configuração: o .env lido pelo core/config.py (pydantic-settings).
# 1. Tenta o DATABASE_URL do .env (padrão: PostgreSQL local)
# 2. Se Postgres estiver fora do ar E DB_AUTO_SQLITE=true, cai para SQLite oculto
#    (útil em dev单机) — mas SEMPRE avisa em qual banco ficou, para ninguém
#    "encher" o Postgres e o app ler do SQLite sem perceber.

DATABASE_URL_PROD = settings.DATABASE_URL


def get_engine():
    """Tenta conectar ao PostgreSQL primeiro, se falhar usa SQLite automaticamente"""
    if DATABASE_URL_PROD.startswith("postgresql"):
        try:
            # Testa conexão com PostgreSQL rapidamente
            temp_engine = create_engine(
                DATABASE_URL_PROD, connect_args={"connect_timeout": 2}
            )
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Conectado ao PostgreSQL com sucesso")
            # Se conectou, retorna engine com pool de conexões
            return create_engine(
                DATABASE_URL_PROD, pool_pre_ping=True, pool_size=10, max_overflow=20
            )
        except Exception as e:
            print(f"⚠️  PostgreSQL não está disponível: {str(e).splitlines()[0]}")
            if not settings.DB_AUTO_SQLITE:
                raise RuntimeError(
                    "PostgreSQL indisponível e DB_AUTO_SQLITE=false — suba o banco "
                    "(docker compose up -d postgres) ou ajuste DATABASE_URL no .env."
                )
            print(
                "🔄 Usando SQLite automaticamente para desenvolvimento "
                "(.smartparking.db OCULTO) — dados NÃO vão para o Postgres!"
            )
            # Fallback para SQLite oculto na pasta do backend
            import os

            sqlite_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), ".smartparking.db"
            )
            sqlite_url = f"sqlite:///{sqlite_path}"
            return create_engine(sqlite_url, connect_args={"check_same_thread": False})
    else:
        return create_engine(
            DATABASE_URL_PROD, connect_args={"check_same_thread": False}
        )


engine = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependência do FastAPI para obter a sessão do banco por requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
