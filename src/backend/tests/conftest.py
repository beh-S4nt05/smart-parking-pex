"""
Fixtures da suíte pytest do backend (M4-01 · ADR-10).

Regra: SQLite em arquivo próprio `.pytest_smartparking.db`, SEM Docker e sem
seed demo — cada teste monta o cenário que precisa pelo fixture `fab`.
O `conftest` precisa setar o environment ANTES de importar o app (o
`core.config` congela `settings` no import).
"""

import os
import pathlib
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

_DB = BACKEND / ".pytest_smartparking.db"
for suffix in ("", "-wal", "-shm"):
    p = pathlib.Path(str(_DB) + suffix)
    if p.exists():
        p.unlink()

os.environ.update({
    "ENVIRONMENT": "test",
    "DEBUG": "False",
    "DATABASE_URL": f"sqlite:///{_DB}",
    "DB_AUTO_SQLITE": "False",
    "SEED_DEMO_ON_STARTUP": "False",
    "SECRET_KEY": "chave-deterministica-de-teste",
    "APP_SIGNING_SECRET": "assinatura-de-teste",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from core.security import criar_hash_senha, criar_token  # noqa: E402
from models.database import Base, engine  # noqa: E402
from models.db_models import (  # noqa: E402
    Andar, Estacionamento, StatusReserva, StatusVaga, TipoUsuario, TipoVaga,
    Usuario, Vaga,
)

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    from main import app

    with TestClient(app) as c:  # `with` dispara o lifespan (zap de reservas)
        yield c


@pytest.fixture()
def db():
    s = sessionmaker(bind=engine)()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


class Fabrica:
    """Monta o cenário mínimo (estacionamento → andar → vagas → usuários)."""

    def __init__(self, db):
        self.db = db
        self._n = 0

    def est(self, nome=None):
        self._n += 1
        e = Estacionamento(
            nome=nome or f"Est QA {self._n}", endereco="Rua QA, 100",
            total_andares=1, total_vagas=0, taxa_hora=10.0,
        )
        self.db.add(e)
        self.db.commit()  # dados visíveis à sessão do TestClient (commit, não flush)
        return e

    def andar(self, est, numero=1, capacidade=4):
        a = Andar(estacionamento_id=est.id, numero_andar=numero, capacidade=capacidade)
        self.db.add(a)
        self.db.commit()
        return a

    def vaga(self, andar, codigo=None, status=StatusVaga.LIVRE, tipo=TipoVaga.COMUM):
        self._n += 1
        v = Vaga(
            andar_id=andar.id, codigo=codigo or f"G{self._n:02d}",
            status=status, tipo=tipo,
        )
        self.db.add(v)
        self.db.commit()
        return v

    def usuario(self, role=TipoUsuario.USUARIO, est=None, senha="senha123"):
        import uuid

        self._n += 1
        sufixo = uuid.uuid4().hex[:8]  # único GLOBAL: a base de teste é um
        role_str = role.value if hasattr(role, "value") else str(role)
        u = Usuario(                     # arquivo só entre testes (sem rollback
            nome=f"User {sufixo}",       # do que os services dão commit)
            email=f"qa{sufixo}@teste.dev",
            senha_hash=criar_hash_senha(senha), role=role_str,
            is_ativo=True, estacionamento_id=est.id if est else None,
        )
        self.db.add(u)
        self.db.commit()
        return u

    def token(self, usuario):
        return {"Authorization": f"Bearer {criar_token(usuario.id, 'access')}"}

@pytest.fixture()
def fab(db):
    return Fabrica(db)
