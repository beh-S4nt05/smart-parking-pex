"""V1: valida expansão do banco e preservação de usuários/reservas existentes."""
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from models.db_models import Base, CredencialEstacionamento, Veiculo


BACKEND = Path(__file__).resolve().parents[1]


def _config(url: str) -> Config:
    conf = Config(str(BACKEND / "alembic.ini"))
    conf.set_main_option("script_location", str(BACKEND / "migrations"))
    conf.set_main_option("sqlalchemy.url", url)
    return conf


def _legado(url: str):
    """Schema mínimo que representa os campos pré-V1 na revisão anterior."""
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE usuarios (
                id VARCHAR PRIMARY KEY,
                nome VARCHAR NOT NULL,
                placa_veiculo VARCHAR,
                is_pcd BOOLEAN NOT NULL DEFAULT false
            )
        """))
        conn.execute(text("""
            CREATE TABLE vagas (
                id VARCHAR PRIMARY KEY,
                tipo VARCHAR NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE reservas (
                id VARCHAR PRIMARY KEY,
                usuario_id VARCHAR NOT NULL,
                vaga_id VARCHAR NOT NULL,
                status VARCHAR NOT NULL
            )
        """))
        conn.execute(text("""
            INSERT INTO usuarios (id,nome,placa_veiculo,is_pcd)
            VALUES ('u1','Motorista Legado','abc1d23',true),
                   ('u2','Sem Veiculo',NULL,false)
        """))
        conn.execute(text("""
            INSERT INTO vagas (id,tipo) VALUES ('v1','pcd')
        """))
        conn.execute(text("""
            INSERT INTO reservas (id,usuario_id,vaga_id,status)
            VALUES ('r1','u1','v1','confirmada')
        """))
    engine.dispose()


def test_migracao_preserva_usuarios_reservas_e_migra_placa(tmp_path):
    url = f"sqlite:///{tmp_path / 'legado.db'}"
    _legado(url)
    conf = _config(url)
    command.stamp(conf, "c4e8b1d2f9a0")
    command.upgrade(conf, "head")

    engine = sa.create_engine(url)
    insp = sa.inspect(engine)
    assert {"veiculos", "credenciais_estacionamento", "auditoria_credenciais"}.issubset(
        set(insp.get_table_names())
    )
    assert {"data_nascimento", "placa_veiculo", "is_pcd"}.issubset(
        {col["name"] for col in insp.get_columns("usuarios")}
    )
    assert {"veiculo_id", "credencial_id"}.issubset(
        {col["name"] for col in insp.get_columns("reservas")}
    )
    assert {"categoria_veiculo", "recarga_disponivel", "conector_tipo"}.issubset(
        {col["name"] for col in insp.get_columns("vagas")}
    )

    with engine.connect() as conn:
        assert conn.execute(text("SELECT status FROM reservas WHERE id='r1'")).scalar() == "confirmada"
        assert conn.execute(text("SELECT veiculo_id FROM reservas WHERE id='r1'")).scalar() is None
        assert conn.execute(text("SELECT is_pcd FROM usuarios WHERE id='u1'")).scalar() == 1
        assert conn.execute(text("SELECT placa FROM veiculos WHERE usuario_id='u1'")).scalar() == "ABC1D23"
        assert conn.execute(text("SELECT motorizacao FROM veiculos WHERE usuario_id='u1'")).scalar() == "nao_informada"
        assert conn.execute(text("SELECT COUNT(*) FROM veiculos WHERE usuario_id='u2'")).scalar() == 0

    # O ORM novo precisa conseguir ler as entidades, com duas FKs para Usuario
    with sa.orm.Session(engine) as db:
        veiculo = db.get(Veiculo, "legacy-u1")
        assert veiculo is not None
        assert veiculo.usuario_id == "u1"
    engine.dispose()


def test_upgrade_nao_duplica_veiculos_se_boot_criou_tabelas(tmp_path):
    url = f"sqlite:///{tmp_path / 'preboot.db'}"
    _legado(url)
    engine = sa.create_engine(url)
    # Simula novo boot criando apenas as tabelas novas antes do Alembic
    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables["veiculos"],
            Base.metadata.tables["credenciais_estacionamento"],
            Base.metadata.tables["auditoria_credenciais"],
        ],
        checkfirst=True,
    )
    engine.dispose()
    conf = _config(url)
    command.stamp(conf, "c4e8b1d2f9a0")
    command.upgrade(conf, "head")
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM veiculos")).scalar() == 1
    engine.dispose()


def test_schema_novo_aceita_veiculo_e_credencial_sem_alterar_reserva(db, fab):
    u = fab.usuario()
    veiculo = Veiculo(usuario_id=u.id, placa="ABC1D23", categoria="carro", motorizacao="eletrico")
    cred = CredencialEstacionamento(usuario_id=u.id, tipo="idoso", status="pendente")
    db.add_all([veiculo, cred])
    db.commit()
    assert veiculo.id is not None
    assert cred.status == "pendente"
