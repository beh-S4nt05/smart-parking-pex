from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Em produção, a URL deve vir de uma variável de ambiente.
# Exemplo: DATABASE_URL=postgresql://user:password@host:port/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/smartparking"
)

# Configuração compatível com PostgreSQL
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
else:
    # Fallback para SQLite em desenvolvimento se não tiver PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependência do FastAPI para obter a sessão do banco por requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
