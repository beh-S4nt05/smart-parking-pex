"""Banco pequeno e determinístico para a suíte Playwright (nunca usa o banco de dev)."""

import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src" / "backend"
DB_PATH = Path(os.environ.get("UI_DATABASE_PATH", "/tmp/smartparking-ui-tests.db"))
for suffix in ("", "-wal", "-shm"):
    candidate = Path(f"{DB_PATH}{suffix}")
    if candidate.exists():
        candidate.unlink()

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DEBUG": "False",
        "DATABASE_URL": f"sqlite:///{DB_PATH}",
        "DB_AUTO_SQLITE": "False",
        "SEED_DEMO_ON_STARTUP": "False",
        "SECRET_KEY": "ui-tests-secret-key-com-mais-de-32-caracteres",
        "APP_SIGNING_SECRET": "ui-tests-signing-key-com-mais-de-32-caracteres",
    }
)
sys.path.insert(0, str(BACKEND))

from core.security import criar_hash_senha
from core.timeutils import utc_agora
from models.database import Base, SessionLocal, engine
from models.db_models import (
    Andar,
    Estacionamento,
    Historico,
    StatusPagamento,
    StatusVaga,
    TipoUsuario,
    TipoVaga,
    Usuario,
    Vaga,
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    centro = Estacionamento(
        nome="Shopping QA Centro",
        endereco="Av. Central, 100 - Centro, Manaus - AM",
        total_andares=2,
        total_vagas=8,
        taxa_hora=8,
        latitude=-3.10,
        longitude=-60.02,
    )
    norte = Estacionamento(
        nome="Shopping QA Norte",
        endereco="Av. Norte, 200 - Cidade Nova, Manaus - AM",
        total_andares=1,
        total_vagas=3,
        taxa_hora=6,
    )
    db.add_all([centro, norte])
    db.flush()

    andar_a = Andar(estacionamento_id=centro.id, numero_andar=1, capacidade=4)
    andar_b = Andar(estacionamento_id=centro.id, numero_andar=2, capacidade=4)
    andar_c = Andar(estacionamento_id=norte.id, numero_andar=1, capacidade=3)
    db.add_all([andar_a, andar_b, andar_c])
    db.flush()

    vagas = [
        Vaga(andar_id=andar_a.id, codigo="A-01", status=StatusVaga.LIVRE, tipo=TipoVaga.COMUM),
        Vaga(andar_id=andar_a.id, codigo="A-02", status=StatusVaga.LIVRE, tipo=TipoVaga.COMUM),
        Vaga(andar_id=andar_a.id, codigo="A-03", status=StatusVaga.OCUPADA, tipo=TipoVaga.COMUM),
        Vaga(andar_id=andar_a.id, codigo="A-04", status=StatusVaga.LIVRE, tipo=TipoVaga.PCD),
        Vaga(andar_id=andar_b.id, codigo="B-01", status=StatusVaga.LIVRE, tipo=TipoVaga.COMUM),
        Vaga(andar_id=andar_b.id, codigo="B-02", status=StatusVaga.LIVRE, tipo=TipoVaga.IDOSO),
        Vaga(andar_id=andar_b.id, codigo="B-03", status=StatusVaga.INATIVA, tipo=TipoVaga.MOTO),
        Vaga(andar_id=andar_b.id, codigo="B-04", status=StatusVaga.LIVRE, tipo=TipoVaga.ELETRICO),
        Vaga(andar_id=andar_c.id, codigo="C-01", status=StatusVaga.LIVRE, tipo=TipoVaga.COMUM),
        Vaga(andar_id=andar_c.id, codigo="C-02", status=StatusVaga.OCUPADA, tipo=TipoVaga.COMUM),
        Vaga(andar_id=andar_c.id, codigo="C-03", status=StatusVaga.LIVRE, tipo=TipoVaga.COMUM),
    ]
    db.add_all(vagas)
    db.flush()

    usuarios = [
        ("Administrador QA", "admin@smartparking.com", "admin123", TipoUsuario.ADMIN, None),
        ("Gestor QA", "gestor@smartparking.com", "gestor123", TipoUsuario.GESTOR, centro),
        (
            "Financeiro QA",
            "financeiro@smartparking.com",
            "financ123",
            TipoUsuario.FINANCEIRO,
            centro,
        ),
        ("Motorista QA", "motorista@smartparking.com", "motor123", TipoUsuario.USUARIO, None),
    ]
    for nome, email, senha, role, estacionamento in usuarios:
        db.add(
            Usuario(
                nome=nome,
                email=email,
                senha_hash=criar_hash_senha(senha),
                role=role.value,
                is_ativo=True,
                estacionamento_id=estacionamento.id if estacionamento else None,
                telefone="92999990000",
            )
        )

    agora = utc_agora()
    db.add(
        Historico(
            estacionamento_id=centro.id,
            vaga_id=vagas[2].id,
            entrada_em=agora - timedelta(hours=2),
            saida_em=agora - timedelta(hours=1),
            tempo_permanencia_minutos=60,
            valor_bruto=8,
            valor_total=8,
            status_pagamento=StatusPagamento.PAGO,
        )
    )
    db.commit()
    print(f"UI QA: banco reiniciado em {DB_PATH} com 2 estacionamentos e 11 vagas")
finally:
    db.close()
