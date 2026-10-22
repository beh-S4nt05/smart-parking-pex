"""Compatibilidade de volume antigo (pós-RF-47): o boot se auto-conserta.

Cenário real visto no Docker do usuário em 22/10: volume Postgres criado
ANTES da RF-47 + código novo → `usuarios` sem a coluna `is_pcd` →
`garantir_admin_padrao` estoura UndefinedColumn → gunicorn não abre a porta
→ healthcheck TCP falha → "dependency backend failed to start". A imagem não
tem alembic (requirements de runtime), então o `main` ganhou
`reparar_esquema_antigo()` — é ele que estes testes exercitam.
"""
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from main import reparar_esquema_antigo
from models.db_models import Base, Usuario

# `usuarios` como ela era na véspera da RF-47 (sem is_pcd)
DDL_ANTIGO = """
CREATE TABLE usuarios (
    id VARCHAR NOT NULL PRIMARY KEY,
    nome VARCHAR NOT NULL,
    email VARCHAR NOT NULL UNIQUE,
    senha_hash VARCHAR NOT NULL,
    telefone VARCHAR,
    placa_veiculo VARCHAR,
    estacionamento_id VARCHAR,
    role VARCHAR NOT NULL,
    is_ativo BOOLEAN DEFAULT 1,
    criado_em TIMESTAMP,
    atualizado_em TIMESTAMP
)
"""


def _banco_velho(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/velho.db")
    with eng.begin() as conn:
        conn.execute(text(DDL_ANTIGO))
        conn.execute(
            text(
                "INSERT INTO usuarios (id, nome, email, senha_hash, role) "
                "VALUES ('u1', 'Admin Legado', 'a@a.dev', 'h', 'admin')"
            )
        )
    return eng


def test_volume_antigo_e_reparado_e_legado_vira_comum(tmp_path):
    eng = _banco_velho(tmp_path)
    reparar_esquema_antigo(eng)
    cols = {c["name"] for c in sa.inspect(eng).get_columns("usuarios")}
    assert "is_pcd" in cols
    with eng.begin() as conn:
        assert conn.execute(text("SELECT is_pcd FROM usuarios")).scalar() == 0
    # o modelo novo consegue LER a linha antiga (era exatamente onde o boot morria)
    with sessionmaker(bind=eng)() as s:
        assert s.get(Usuario, "u1").is_pcd is False


def test_reparo_e_idempotente(tmp_path):
    eng = _banco_velho(tmp_path)
    reparar_esquema_antigo(eng)
    reparar_esquema_antigo(eng)  # segunda passada não explode nem duplica
    with eng.begin() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM pragma_table_info('usuarios') WHERE name='is_pcd'")
        ).scalar()
    assert n == 1


def test_banco_novo_ou_vazio_e_noop(tmp_path):
    # banco já no estado novo (create_all com a coluna)...
    eng = create_engine(f"sqlite:///{tmp_path}/novo.db")
    Base.metadata.create_all(eng)
    reparar_esquema_antigo(eng)  # não faz nada
    # ...e banco sem tabela nenhuma (primeira execução real)
    vazio = create_engine(f"sqlite:///{tmp_path}/vazio.db")
    reparar_esquema_antigo(vazio)  # inspecionar tabela inexistente é silencioso
