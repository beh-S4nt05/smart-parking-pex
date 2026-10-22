"""M2-05/M3-07 (ACH-10) + RF-23/RF-25 — expiração de reservas e histórico."""

from datetime import timedelta

from core.timeutils import utc_agora
from models.db_models import Historico, Reserva, StatusReserva, StatusVaga, Vaga
from models.schemas import ReservaCreate, VagaAtualizaStatus
from rules import reserva_service, vaga_service


def test_sweep_expira_reserva_e_libera_vaga(db, fab):
    est = fab.est(); andar = fab.andar(est); vaga = fab.vaga(andar)
    motorista = fab.usuario()
    agora = utc_agora()
    r = Reserva(
        usuario_id=motorista.id, vaga_id=vaga.id,
        horario_inicio=agora - timedelta(hours=3),
        horario_fim=agora - timedelta(hours=1),
        status=StatusReserva.CONFIRMADA,
    )
    db.add(r)
    vaga.status = StatusVaga.RESERVADA
    db.commit()

    assert reserva_service.expirar_reservas_vencidas(db) == 1
    db.refresh(r); db.refresh(vaga)
    assert r.status == StatusReserva.EXPIRADA
    assert vaga.status == StatusVaga.LIVRE
    # idempotente: segunda varredura não acha mais nada
    assert reserva_service.expirar_reservas_vencidas(db) == 0


def test_reserva_futura_nao_e_touchada_pelo_sweep(db, fab):
    est = fab.est(); andar = fab.andar(est); vaga = fab.vaga(andar)
    motorista = fab.usuario()
    agora = utc_agora()
    r = Reserva(
        usuario_id=motorista.id, vaga_id=vaga.id,
        horario_inicio=agora + timedelta(hours=1),
        horario_fim=agora + timedelta(hours=3),
        status=StatusReserva.CONFIRMADA,
    )
    db.add(r); db.commit()
    assert reserva_service.expirar_reservas_vencidas(db) == 0


def test_ciclo_completo_reserva_cancelamento(db, fab):
    est = fab.est(); andar = fab.andar(est); vaga = fab.vaga(andar)
    motorista = fab.usuario()
    agora = utc_agora()
    nova = reserva_service.criar_reserva(
        db,
        ReservaCreate(
            vaga_id=vaga.id,
            horario_inicio=agora + timedelta(minutes=15),
            horario_fim=agora + timedelta(hours=2),
        ),
        motorista,
    )
    assert vaga.status == StatusVaga.RESERVADA
    reserva_service.cancelar_reserva(db, nova.id, motorista)
    db.refresh(vaga)
    assert vaga.status == StatusVaga.LIVRE


def test_chegada_em_vaga_reservada_abre_estadia_e_conclui_reserva(db, fab):
    """RF-25 (⬜→✅): RESERVADA→OCUPADA cria o Histórico E dá baixa na reserva."""
    est = fab.est(); andar = fab.andar(est); vaga = fab.vaga(andar)
    motorista = fab.usuario()
    agora = utc_agora()
    nova = reserva_service.criar_reserva(
        db,
        ReservaCreate(
            vaga_id=vaga.id,
            horario_inicio=agora - timedelta(minutes=5),
            horario_fim=agora + timedelta(hours=1),
        ),
        motorista,
    )

    # motorista chegou: vaga reservada → ocupada
    vaga_service.atualizar_status_vaga(
        db,
        vaga.id,
        VagaAtualizaStatus(status=StatusVaga.OCUPADA, origem="app_motorista"),
    )
    db.refresh(nova)
    assert nova.status == StatusReserva.CONCLUIDA

    hist = (
        db.query(Historico)
        .filter(Historico.vaga_id == vaga.id)
        .one()
    )
    assert hist.saida_em is None  # estadia ABERTA pela chegada
    assert hist.origem == "app_motorista"

    # saída fecha o histórico com tempo inteiro (RN-02)
    vaga_service.atualizar_status_vaga(
        db, vaga.id, VagaAtualizaStatus(status=StatusVaga.LIVRE, origem="manual")
    )
    db.refresh(hist)
    assert hist.saida_em is not None
    assert isinstance(hist.tempo_permanencia_minutos, int)


def test_lote_de_vagas_tipo_e_totais_coerentes(db, fab):
    """ACH-17/M3-09: lote aceita tipo e atualiza capacidade/total_vagas."""
    from rules.admin_service import criar_vagas_em_lote

    est = fab.est(); andar = fab.andar(est, capacidade=4)
    criar_vagas_em_lote(db, andar.id, 3, prefixo_codigo="QA", tipo="pcd")
    criadas = db.query(Vaga).filter(Vaga.andar_id == andar.id).all()
    assert len(criadas) == 3
    assert all(v.tipo == "pcd" and v.codigo.startswith("QA") for v in criadas)
    db.refresh(andar); db.refresh(est)
    # capacidade espelha o NÚMERO REAL de vagas do andar (0 + 3), não a soma nominal
    assert andar.capacidade == 3
    assert est.total_vagas == 3
