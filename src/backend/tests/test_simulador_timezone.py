"""Regressões de timestamp para simulador/estadia em bancos SQLite e PostgreSQL.

Em PostgreSQL, DateTime(timezone=True) retorna datetime aware, enquanto utc_agora()
produz naive-UTC. O bug em produção era TypeError no fechamento da vaga via lote.
"""

from datetime import timedelta, timezone

import pytest
from sqlalchemy import event
from sqlalchemy.orm.attributes import set_committed_value

from core.timeutils import FUSO_MANAUS, normalizar, utc_agora
from models.db_models import ConfiguracaoPreco, Historico, StatusVaga, TipoUsuario
from rules import pagamento_service, vaga_service


@pytest.mark.parametrize("fuso", [timezone.utc, FUSO_MANAUS], ids=["utc", "manaus"])
def test_patch_lote_fecha_estadia_aware_como_postgres(client, db, fab, fuso):
    """O mesmo endpoint e sequência que retornavam 500 na máquina do usuário."""
    est = fab.est()
    andar = fab.andar(est)
    vaga = fab.vaga(andar)
    admin = fab.token(fab.usuario(role=TipoUsuario.ADMIN))

    def enviar(status):
        return client.patch(
            "/api/vagas/lote/status",
            json={"vaga_ids": [vaga.id], "status": status, "origem": "simulador"},
            headers=admin,
        )

    entrada = enviar("ocupada")
    assert entrada.status_code == 200, entrada.text
    historico = db.query(Historico).filter(Historico.vaga_id == vaga.id).one()
    historico.entrada_em = utc_agora() - timedelta(minutes=37)
    db.commit()

    def simular_driver_postgres(objeto, _contexto):
        if objeto.vaga_id == vaga.id and objeto.entrada_em is not None:
            # O PostgreSQL devolve timestamptz aware; SQLite normalmente naive.
            aware = objeto.entrada_em.replace(tzinfo=timezone.utc).astimezone(fuso)
            set_committed_value(objeto, "entrada_em", aware)

    event.listen(Historico, "load", simular_driver_postgres)
    try:
        saida = enviar("livre")
    finally:
        event.remove(Historico, "load", simular_driver_postgres)

    assert saida.status_code == 200, saida.text
    assert saida.json()["atualizadas"] == 1
    db.expire_all()
    historico = db.query(Historico).filter(Historico.vaga_id == vaga.id).one()
    assert historico.saida_em is not None
    assert 37 <= historico.tempo_permanencia_minutos <= 38
    assert normalizar(historico.saida_em) > normalizar(historico.entrada_em)
    assert db.get(type(vaga), vaga.id).status == StatusVaga.LIVRE

    # Reaplicar o mesmo status não cria outra saída/entrada.
    novamente = enviar("livre")
    assert novamente.status_code == 200, novamente.text
    assert novamente.json()["atualizadas"] == 0
    assert db.query(Historico).filter(Historico.vaga_id == vaga.id).count() == 1


@pytest.mark.parametrize("fuso", [timezone.utc, FUSO_MANAUS], ids=["utc", "manaus"])
def test_saida_por_update_individual_aceita_datetime_aware(db, fab, fuso):
    """Também protege o caminho não-lote (sensor/manual)."""
    from models.schemas import VagaAtualizaStatus

    est = fab.est()
    vaga = fab.vaga(fab.andar(est), status=StatusVaga.OCUPADA)
    fim = utc_agora()
    entrada = (fim - timedelta(minutes=21)).replace(tzinfo=timezone.utc).astimezone(fuso)
    registro = Historico(
        estacionamento_id=est.id, vaga_id=vaga.id,
        entrada_em=entrada, origem="sensor",
    )
    db.add(registro)
    db.flush()

    vaga_service.atualizar_status_vaga(
        db, vaga.id, VagaAtualizaStatus(status=StatusVaga.LIVRE, origem="sensor"),
    )
    db.refresh(registro)
    assert registro.tempo_permanencia_minutos == 21
    assert registro.saida_em is not None


def test_recalculo_tarifa_aceita_entrada_manaus_e_saida_naive_utc(db, fab):
    """A mesma operação aritmética também existe no fallback financeiro."""
    est = fab.est()
    vaga = fab.vaga(fab.andar(est), status=StatusVaga.LIVRE)
    db.add(ConfiguracaoPreco(
        estacionamento_id=est.id, tipo_vaga="comum",
        valor_hora=10.0, valor_diaria=90.0, tolerancia_minutos=0,
    ))

    fim = utc_agora()
    registro = Historico(
        estacionamento_id=est.id,
        vaga_id=vaga.id,
        entrada_em=(fim - timedelta(minutes=65)).replace(tzinfo=timezone.utc).astimezone(FUSO_MANAUS),
        saida_em=fim,
        tempo_permanencia_minutos=None,
    )
    db.add(registro)
    db.flush()

    resultado = pagamento_service.calcular_tarifa_estadia(db, registro.id)
    assert resultado["tempo_permanencia_minutos"] == 65
    assert resultado["valor_total"] == 20.0
