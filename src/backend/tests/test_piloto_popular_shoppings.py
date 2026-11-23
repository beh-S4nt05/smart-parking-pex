"""Piloto publico V1: somente dados ficticios, sem credenciais padrão."""
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from models.db_models import Andar, Base, Estacionamento, StatusVaga, Usuario, Vaga
from rules.estacionamento_service import buscar_estacionamento_por_id, listar_todos_estacionamentos
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


def test_vitrine_usa_mesma_contagem_por_andar_do_detalhe(banco_piloto):
    est = Estacionamento(nome="QA Contagem", endereco="Testes", total_andares=2, total_vagas=99)
    banco_piloto.add(est)
    banco_piloto.flush()
    a1 = Andar(estacionamento_id=est.id, numero_andar=1, capacidade=4)
    a2 = Andar(estacionamento_id=est.id, numero_andar=2, capacidade=0)
    banco_piloto.add_all([a1, a2])
    banco_piloto.flush()
    for i, status in enumerate(
        [StatusVaga.LIVRE, StatusVaga.OCUPADA, StatusVaga.RESERVADA, StatusVaga.INATIVA]
    ):
        banco_piloto.add(Vaga(andar_id=a1.id, codigo=f"A-{i+1:02d}", status=status))
    banco_piloto.commit()

    vitrine = listar_todos_estacionamentos(banco_piloto)
    assert len(vitrine) == 1
    assert vitrine[0].total_vagas == 4
    assert vitrine[0].vagas_disponiveis_total == 1
    assert [(a.vagas_livres, a.vagas_ocupadas) for a in vitrine[0].andares] == [
        (1, 2), (0, 0)
    ]

    detalhe = buscar_estacionamento_por_id(banco_piloto, est.id)
    assert detalhe is not None
    assert detalhe.vagas_disponiveis_total == sum(
        a.vagas_livres for a in detalhe.andares
    )

    # Nova ocupacao na base: a vitrine deve refletir a mudança sem reexecutar seed.
    vaga = banco_piloto.query(Vaga).filter(Vaga.codigo == "A-01").one()
    vaga.status = StatusVaga.OCUPADA
    banco_piloto.commit()
    atualizada = listar_todos_estacionamentos(banco_piloto)[0]
    assert atualizada.vagas_disponiveis_total == 0
    assert atualizada.andares[0].vagas_ocupadas == 3
    assert atualizada.andares[0].vagas_livres == 0
