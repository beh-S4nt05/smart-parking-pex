"""Verifica endereços reais, seed e migração seletiva sem reset de dados."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.db_models import Base, Estacionamento
from piloto_corrigir_localizacoes import corrigir
from seed_demo import SHOPPINGS


def test_oito_enderecos_verificados_do_seed_manaus():
    esperado = {
        "Amazonas Shopping": "Av. Djalma Batista, 482",
        "Manauara Shopping": "Av. Mário Ypiranga Monteiro, 1300",
        "Sumaúma Park Shopping": "Av. Noel Nutels, 1762",
        "Ponta Negra Shopping": "Av. Coronel Teixeira, 5705",
        "Millennium Shopping": "Av. Djalma Batista, 1661",
        "Studio 5 Festival Mall": "Av. Rodrigo Otávio, 3555",
        "Shopping Manaus ViaNorte": "Av. Arquiteto José Henrique Bento Rodrigues, 3541",
        "Shopping Phelippe Daou": "Av. Camapuã, 2939",
    }
    assert len(SHOPPINGS) == len(esperado) == 8
    assert {s["nome"] for s in SHOPPINGS} == set(esperado)
    for shopping in SHOPPINGS:
        assert esperado[shopping["nome"]] in shopping["endereco"]
        assert "Manaus - AM" in shopping["endereco"]
        assert shopping["latitude"] is None
        assert shopping["longitude"] is None


def test_corrigir_seed_legado_dry_run_apply_e_isolamento(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/rotas.sqlite")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        antigo = Estacionamento(
            nome="Shopping Norte",
            endereco="Av. Camapuã, 1480 - Cidade Nova, Manaus - AM",
            latitude=-3.0474,
            longitude=-59.9876,
            total_andares=1,
            total_vagas=0,
        )
        editado = Estacionamento(
            nome="Amazonas Shopping",
            endereco="Local personalizado da administração",
            latitude=-3.12,
            longitude=-60.10,
            total_andares=1,
            total_vagas=0,
        )
        db.add_all([antigo, editado])
        db.commit()
        chave = antigo.id
        chave_editado = editado.id

        candidatos, ignorados = corrigir(db, aplicar=False)
        assert candidatos == 1
        assert ignorados == 1
        assert db.get(Estacionamento, chave).nome == "Shopping Norte"

        candidatos, ignorados = corrigir(db, aplicar=True)
        assert candidatos == 1
        assert ignorados == 1
        atualizado = db.get(Estacionamento, chave)
        assert atualizado.nome == "Shopping Manaus ViaNorte"
        assert "Bento Rodrigues, 3541" in atualizado.endereco
        assert atualizado.latitude is None
        assert atualizado.longitude is None

        preservado = db.get(Estacionamento, chave_editado)
        assert preservado.endereco == "Local personalizado da administração"
        assert preservado.latitude == -3.12
        assert corrigir(db, aplicar=True)[0] == 0
    engine.dispose()
