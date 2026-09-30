from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 🔧 Configuração automática para desenvolvimento:
# 1. Primeiro tenta conectar no PostgreSQL
# 2. Se o PostgreSQL não estiver rodando, cai automaticamente para SQLite arquivo oculto
# sem precisar de configuração manual

DATABASE_URL_PROD = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/smartparking"
)


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
            print(
                "🔄 Usando SQLite automaticamente para desenvolvimento (.smartparking.db OCULTO)..."
            )
            # Fallback para SQLite oculto na pasta do backend
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
