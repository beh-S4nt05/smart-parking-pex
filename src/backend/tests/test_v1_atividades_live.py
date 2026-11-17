"""Regressão V1: auditoria das ações no painel, isolamento por shopping e receita real."""

from datetime import timedelta

from core.timeutils import utc_agora
from models.db_models import (
    ConfiguracaoPreco,
    EventoOperacional,
    Historico,
    TipoUsuario,
)
from models.schemas import ReservaCreate, VagaAtualizaStatus
from rules import pagamento_service, reserva_service, vaga_service


def _reserva(db, vaga, motorista):
    agora = utc_agora()
    return reserva_service.criar_reserva(
        db,
        ReservaCreate(
            vaga_id=vaga.id,
            horario_inicio=agora + timedelta(minutes=2),
            horario_fim=agora + timedelta(hours=1),
        ),
        motorista,
    )


def test_reservar_cancelar_e_relatorio_por_estacionamento(client, db, fab):
    proprio, alheio = fab.est(), fab.est()
    vaga = fab.vaga(fab.andar(proprio))
    fab.vaga(fab.andar(alheio))
    motorista = fab.usuario()
    gestor = fab.token(fab.usuario(role=TipoUsuario.GESTOR, est=proprio))
    financeiro = fab.token(fab.usuario(role=TipoUsuario.FINANCEIRO, est=proprio))
    admin = fab.token(fab.usuario(role=TipoUsuario.ADMIN))

    r = _reserva(db, vaga, motorista)
    reserva_id = r.id
    r = reserva_service.cancelar_reserva(db, reserva_id, motorista)
    assert r.status == "cancelada"

    operacoes = db.query(EventoOperacional).filter_by(reserva_id=reserva_id).all()
    assert [op.evento for op in operacoes] == ["reserva_criada", "reserva_cancelada"]
    assert all(op.usuario_id == motorista.id for op in operacoes)

    for headers in (admin, gestor, financeiro):
        resp = client.get(
            "/api/admin/eventos",
            params={"estacionamento_id": proprio.id, "limite": 20},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        eventos = resp.json()
        relevantes = [e for e in eventos if e.get("reserva_id") == reserva_id]
        assert {e["evento"] for e in relevantes} == {
            "reserva_criada", "reserva_cancelada"
        }
        assert all(e["usuario_nome"] == motorista.nome for e in relevantes)
        assert all(e["vaga_codigo"] == vaga.codigo for e in relevantes)

        resumo = client.get(
            "/api/admin/atividades/resumo",
            params={"estacionamento_id": proprio.id, "periodo": "diario"},
            headers=headers,
        )
        assert resumo.status_code == 200, resumo.text
        contagens = resumo.json()
        assert contagens["reservas_criadas"] == 1
        assert contagens["reservas_canceladas"] == 1
        assert contagens["pagamentos_confirmados"] == 0

    for headers in (gestor, financeiro):
        assert client.get("/api/admin/eventos", params={"estacionamento_id": alheio.id}, headers=headers).status_code == 403
        assert client.get("/api/admin/atividades/resumo", params={"estacionamento_id": alheio.id}, headers=headers).status_code == 403
        assert client.get("/api/admin/eventos", headers=headers).status_code == 200
        assert client.get("/api/admin/atividades/resumo", headers=headers).status_code == 200

    assert client.get("/api/admin/eventos", headers=fab.token(motorista)).status_code == 403
    assert client.get("/api/admin/atividades/resumo").status_code == 401


def test_reserva_expira_uma_vez_e_checkin_registra_fluxo(db, fab):
    est = fab.est()
    andar = fab.andar(est)
    vaga_expira, vaga_checkin = fab.vaga(andar), fab.vaga(andar)
    motorista = fab.usuario()
    vencida = _reserva(db, vaga_expira, motorista)
    vencida.horario_fim = utc_agora() - timedelta(minutes=2)
    db.commit()

    assert reserva_service.expirar_reservas_vencidas(db) >= 1
    assert reserva_service.expirar_reservas_vencidas(db) == 0
    expiracoes = db.query(EventoOperacional).filter_by(
        reserva_id=vencida.id, evento="reserva_expirada",
    ).count()
    assert expiracoes == 1

    confirmada = _reserva(db, vaga_checkin, motorista)
    vaga_service.atualizar_status_vaga(
        db, vaga_checkin.id,
        VagaAtualizaStatus(status="ocupada", origem="simulador"),
    )
    db.refresh(confirmada)
    assert confirmada.status == "concluida"
    assert db.query(EventoOperacional).filter_by(
        reserva_id=confirmada.id, evento="reserva_concluida",
    ).count() == 1


def test_pagamento_confirmado_entra_na_auditoria_sem_contar_reserva(db, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    motorista = fab.usuario()
    db.add(ConfiguracaoPreco(
        estacionamento_id=est.id, tipo_vaga="comum",
        valor_hora=10, tolerancia_minutos=0,
    ))
    fim = utc_agora()
    hist = Historico(
        estacionamento_id=est.id, vaga_id=vaga.id, usuario_id=motorista.id,
        entrada_em=fim - timedelta(minutes=90), saida_em=fim,
    )
    db.add(hist)
    db.commit()

    pagamento = pagamento_service.registrar_pagamento(
        db, hist.id, "dinheiro", valor_recebido=20.0,
    )
    assert pagamento["pagamento"].valor_total == 20.0
    eventos = db.query(EventoOperacional).filter_by(
        historico_id=hist.id, evento="pagamento_confirmado",
    ).all()
    assert len(eventos) == 1
    assert eventos[0].valor == 20.0
    assert eventos[0].usuario_id == motorista.id
    assert db.query(EventoOperacional).filter_by(
        historico_id=hist.id, evento="reserva_criada",
    ).count() == 0
