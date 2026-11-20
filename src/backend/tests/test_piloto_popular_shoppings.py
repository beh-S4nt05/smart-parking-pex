"""Piloto publico V1: somente dados ficticios, sem credenciais padrão."""
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from models.db_models import Andar, Base, Estacionamento, Usuario, Vaga
from piloto_popular_shoppings import popular_shoppings_piloto
from seed_demo import SHOPPINGS


@pytest.fixture()
def banco_piloto(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/piloto.db")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_dry_run_nao_insere_nada(banco_piloto):
    n, a, v = popular_shoppings_piloto(banco_piloto, aplicar=False)
    assert n == 8
    assert a > 8
    assert v > 1000
    assert banco_piloto.scalar(select(func.count()).select_from(Estacionamento)) == 0
    assert banco_piloto.scalar(select(func.count()).select_from(Usuario)) == 0


def test_semente_segura_nunca_cria_contas_e_eh_idempotente(banco_piloto):
    n, a, v = popular_shoppings_piloto(banco_piloto, aplicar=True)
    assert n == 8
    assert banco_piloto.scalar(select(func.count()).select_from(Andar)) == a
    assert banco_piloto.scalar(select(func.count()).select_from(Vaga)) == v
    assert banco_piloto.scalar(select(func.count()).select_from(Usuario)) == 0
    assert {s.nome for s in banco_piloto.query(Estacionamento).all()} == {
        s["nome"] for s in SHOPPINGS
    }
    assert banco_piloto.query(Estacionamento).filter(
        Estacionamento.nome == "Studio 5 Festival Mall"
    ).one().endereco.startswith("Av. Rodrigo Otávio, 3555")
    assert popular_shoppings_piloto(banco_piloto, aplicar=True) == (0, 0, 0)
    assert banco_piloto.scalar(select(func.count()).select_from(Vaga)) == v


def test_piloto_nunca_altera_estacionamento_existente(banco_piloto):
    manual = Estacionamento(
        nome="Cadastro do gestor",
        endereco="Rua própria cadastrada manualmente",
        total_andares=1,
        total_vagas=0,
    )
    banco_piloto.add(manual)
    banco_piloto.commit()
    assert popular_shoppings_piloto(banco_piloto, aplicar=True) == (0, 0, 0)
    assert banco_piloto.query(Estacionamento).one().nome == "Cadastro do gestor"
    assert banco_piloto.scalar(select(func.count()).select_from(Vaga)) == 0
