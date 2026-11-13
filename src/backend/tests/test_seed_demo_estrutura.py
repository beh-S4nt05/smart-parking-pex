"""Guarda da estrutura de contas do seed demo (RF: atribuição de acessos).

O seed deve garantir, de forma idempotente e autorreparante:

* ``admin@smartparking.com`` — admin global, sem vínculo (gerencia todos).
* ``gestor@smartparking.com`` — GESTOR de Amazonas Shopping + Millennium Shopping.
* ``financeiro@smartparking.com`` — GESTOR do Amazonas Shopping.
* ``financeiro<N>@smartparking.com`` — um FINANCEIRO por shopping (N sequencial
  até a quantidade de shoppings cadastrados; nunca mais de um por shopping).
* ``gestor<N>@smartparking.com`` — um GESTOR por shopping que não tem o gestor
  clássico.
* Senhas padrões sempre válidas para as contas de demo.
"""

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from core.security import verificar_senha
from models.db_models import Base, TipoUsuario, Usuario, usuario_estacionamentos
from seed_demo import popular_database


@pytest.fixture()
def seed_db(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/seed.db")
    Base.metadata.create_all(bind=eng)
    s = sessionmaker(bind=eng)()
    try:
        yield s
    finally:
        s.close()
        eng.dispose()


def _por_email(db, email):
    return db.query(Usuario).filter(Usuario.email == email).one()


def test_seed_cria_estrutura_completa(seed_db):
    resumo = popular_database(seed_db)
    assert resumo["estacionamentos"] == 8

    usuarios = seed_db.query(Usuario).all()
    assert len(usuarios) == 18  # 4 clássico + 8 financeiros + 6 gestores próprios


def test_admin_global_sem_vinculo(seed_db):
    popular_database(seed_db)
    admin = _por_email(seed_db, "admin@smartparking.com")
    assert admin.role == TipoUsuario.ADMIN.value
    assert admin.estacionamento_id is None
    assert not admin.estacionamentos_vinculados
    assert verificar_senha("admin123", admin.senha_hash)


def test_gestor_classico_tem_amazonas_e_millennium(seed_db):
    popular_database(seed_db)
    from models.db_models import Estacionamento

    gestor = _por_email(seed_db, "gestor@smartparking.com")
    assert gestor.role == TipoUsuario.GESTOR.value
    nomes = {e.nome for e in gestor.estacionamentos_vinculados}
    assert nomes == {"Millennium Shopping"}
    assert gestor.estacionamento_id is not None
    assert seed_db.get(Estacionamento, gestor.estacionamento_id).nome == "Amazonas Shopping"
    assert verificar_senha("gestor123", gestor.senha_hash)


def test_financeiro_classico_virou_gestor_do_amazonas(seed_db):
    popular_database(seed_db)
    u = _por_email(seed_db, "financeiro@smartparking.com")
    assert u.role == TipoUsuario.GESTOR.value
    from models.db_models import Estacionamento

    assert seed_db.get(Estacionamento, u.estacionamento_id).nome == "Amazonas Shopping"
    assert verificar_senha("gestor123", u.senha_hash)


def test_um_financeiro_por_shopping_sema_duplicatas(seed_db):
    popular_database(seed_db)
    fins = (
        seed_db.query(Usuario)
        .filter(Usuario.role == TipoUsuario.FINANCEIRO.value)
        .all()
    )
    assert len(fins) == 8
    por_est = {}
    for f in fins:
        por_est.setdefault(f.estacionamento_id, []).append(f.email)
    for est_id, emails in por_est.items():
        assert len(emails) == 1, f"shopping {est_id} tem {len(emails)} financeiros"
    # e-mails numerados sequencialmente
    emails = sorted(f.email for f in fins)
    assert emails[0] == "financeiro1@smartparking.com"
    assert emails[-1] == "financeiro8@smartparking.com"
    for f in fins:
        assert verificar_senha("financ123", f.senha_hash)


def test_gestores_proprios_cobrem_shoppings_sem_gestor_classico(seed_db):
    popular_database(seed_db)
    from models.db_models import Estacionamento

    gestores = (
        seed_db.query(Usuario)
        .filter(Usuario.role == TipoUsuario.GESTOR.value)
        .all()
    )
    # gestor@ + financeiro@ (ambos do Amazonas) + gestor2..8 (6 shoppings)
    assert len(gestores) == 8

    por_est = {}
    for g in gestores:
        por_est.setdefault(g.estacionamento_id, []).append(g.email)
    # Amazonas tem 2 gestores (pedido explícito); cada um dos demais, 1
    nomes_por_est = {
        seed_db.get(Estacionamento, est_id).nome: emails
        for est_id, emails in por_est.items()
    }
    assert len(nomes_por_est["Amazonas Shopping"]) == 2
    for nome, emails in nomes_por_est.items():
        if nome == "Amazonas Shopping":
            continue
        assert len(emails) == 1, f"{nome} tem {len(emails)} gestores"
    # Millennium não tem gestor próprio (principal): é coberto pelo vínculo
    # N:N do gestor@ (verificado em test_gestor_classico_tem_amazonas_e_millennium).
    assert "Millennium Shopping" not in nomes_por_est


def test_seed_idempotente_nao_duplica_contas_ou_vinculos(seed_db):
    popular_database(seed_db)
    n1 = seed_db.query(Usuario).count()
    popular_database(seed_db)
    n2 = seed_db.query(Usuario).count()
    assert n1 == n2 == 18
    dupes = seed_db.execute(
        select(
            usuario_estacionamentos.c.usuario_id,
            usuario_estacionamentos.c.estacionamento_id,
            func.count(),
        )
        .group_by(
            usuario_estacionamentos.c.usuario_id,
            usuario_estacionamentos.c.estacionamento_id,
        )
        .having(func.count() > 1)
    ).all()
    assert not dupes


def test_seed_repara_base_antiga(seed_db):
    """Base com a estrutura anterior é corrigida pelo seed (autorreparo)."""
    from core.security import criar_hash_senha
    from models.db_models import Estacionamento

    est_a = Estacionamento(
        nome="Amazonas Shopping", endereco="x", total_andares=1,
        total_vagas=1, taxa_hora=8,
    )
    est_m = Estacionamento(
        nome="Millennium Shopping", endereco="y", total_andares=1,
        total_vagas=1, taxa_hora=6,
    )
    seed_db.add_all([est_a, est_m])
    seed_db.flush()
    antigo = Usuario(
        nome="Financeiro Central", email="financeiro@smartparking.com",
        senha_hash=criar_hash_senha("senha-antiga"),
        role=TipoUsuario.FINANCEIRO.value, estacionamento_id=est_m.id,
        is_ativo=True,
    )
    seed_db.add(antigo)
    seed_db.commit()

    popular_database(seed_db)
    u = _por_email(seed_db, "financeiro@smartparking.com")
    assert u.role == TipoUsuario.GESTOR.value
    assert seed_db.get(Estacionamento, u.estacionamento_id).nome == "Amazonas Shopping"
    assert verificar_senha("gestor123", u.senha_hash)
    assert not verificar_senha("senha-antiga", u.senha_hash)

    gestor = _por_email(seed_db, "gestor@smartparking.com")
    assert {e.nome for e in gestor.estacionamentos_vinculados} == {"Millennium Shopping"}
    assert seed_db.get(Estacionamento, gestor.estacionamento_id).nome == "Amazonas Shopping"
