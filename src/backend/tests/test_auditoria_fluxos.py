"""Regressões da auditoria ponta a ponta — sessão, reserva, admin e caixa."""

from datetime import timedelta
import uuid

import pytest
from fastapi import HTTPException

from core.security import criar_token
from core.timeutils import utc_agora
from models.db_models import (
    ConfiguracaoPreco,
    CupomDesconto,
    Historico,
    StatusReserva,
    StatusPagamento,
    Usuario,
)
from models.schemas import ReservaCreate, VagaAtualizaStatus
from rules import pagamento_service, reserva_service, vaga_service


def _admin_headers(db):
    admin = db.query(Usuario).filter(Usuario.email == "admin@smartparking.com").one()
    return {"Authorization": f"Bearer {criar_token(admin.id, 'access')}"}


def _reserva(db, fab):
    est = fab.est()
    andar = fab.andar(est)
    vaga = fab.vaga(andar)
    motorista = fab.usuario()
    agora = utc_agora()
    reserva = reserva_service.criar_reserva(
        db,
        ReservaCreate(
            vaga_id=vaga.id,
            horario_inicio=agora + timedelta(minutes=5),
            horario_fim=agora + timedelta(hours=2),
        ),
        motorista,
    )
    return reserva, vaga, motorista


@pytest.mark.parametrize("status_final", [StatusReserva.CONCLUIDA, StatusReserva.EXPIRADA])
def test_reserva_encerrada_nao_pode_ser_cancelada(db, fab, status_final):
    reserva, _vaga, motorista = _reserva(db, fab)
    reserva.status = status_final
    db.commit()

    with pytest.raises(HTTPException) as exc:
        reserva_service.cancelar_reserva(db, reserva.id, motorista)
    assert exc.value.status_code == 400
    db.refresh(reserva)
    assert reserva.status == status_final


def test_checkin_de_reserva_vincula_estadia_ao_motorista(db, fab):
    reserva, vaga, motorista = _reserva(db, fab)
    motorista.placa_veiculo = "QA1B234"
    db.commit()

    vaga_service.atualizar_status_vaga(
        db, vaga.id, VagaAtualizaStatus(status="ocupada", origem="app_motorista")
    )

    hist = db.query(Historico).filter(Historico.vaga_id == vaga.id).one()
    assert hist.usuario_id == motorista.id
    assert hist.placa_veiculo == "QA1B234"
    db.refresh(reserva)
    assert reserva.status == StatusReserva.CONCLUIDA


def _estadia(db, fab, *, minutos=75, est=None):
    est = est or fab.est()
    andar = fab.andar(est)
    vaga = fab.vaga(andar)
    agora = utc_agora()
    hist = Historico(
        estacionamento_id=est.id,
        vaga_id=vaga.id,
        entrada_em=agora - timedelta(minutes=minutos),
        saida_em=agora,
        tempo_permanencia_minutos=minutos,
    )
    db.add(hist)
    db.commit()
    return est, hist


def _preco(db, est):
    preco = ConfiguracaoPreco(
        estacionamento_id=est.id,
        tipo_vaga="comum",
        valor_hora=10.0,
        valor_diaria=80.0,
        tolerancia_minutos=15,
    )
    db.add(preco)
    db.commit()
    return preco


def _cupom(db, est, tipo="valor_fixo", valor=4.0):
    cupom = CupomDesconto(
        estacionamento_id=est.id,
        codigo=f"QA{uuid.uuid4().hex[:10].upper()}",
        tipo_desconto=tipo,
        valor_desconto=valor,
        limite_usos=10,
        usos_realizados=0,
        ativo=True,
    )
    db.add(cupom)
    db.commit()
    return cupom


def test_registrar_pagamento_calcula_tarifa_pendente(db, fab):
    est, hist = _estadia(db, fab)
    _preco(db, est)

    resultado = pagamento_service.registrar_pagamento(
        db, hist.id, "dinheiro", valor_recebido=20.0
    )

    assert resultado["pagamento"].valor_total == 10.0
    assert resultado["troco"] == 10.0
    db.refresh(hist)
    assert hist.status_pagamento == StatusPagamento.PAGO


def test_tarifa_nao_muda_depois_do_pagamento(db, fab):
    est, hist = _estadia(db, fab)
    _preco(db, est)
    pagamento_service.calcular_tarifa_estadia(db, hist.id)
    pagamento_service.registrar_pagamento(db, hist.id, "dinheiro", 10.0)

    with pytest.raises(HTTPException) as exc:
        pagamento_service.calcular_tarifa_estadia(db, hist.id)
    assert exc.value.status_code == 400


def test_isencao_total_so_fecha_no_pagamento(db, fab):
    est, hist = _estadia(db, fab)
    _preco(db, est)
    cupom = _cupom(db, est, tipo="isencao_total", valor=100.0)

    tarifa = pagamento_service.calcular_tarifa_estadia(db, hist.id, cupom.codigo)
    assert tarifa["valor_total"] == 0.0
    db.refresh(hist)
    assert hist.status_pagamento == StatusPagamento.PENDENTE

    pagamento_service.registrar_pagamento(db, hist.id, "dinheiro", 0.0)
    db.refresh(cupom)
    db.refresh(hist)
    assert cupom.usos_realizados == 1
    assert hist.status_pagamento == StatusPagamento.PAGO


def test_confirmacao_pix_contabiliza_caixa_e_cupom(db, fab):
    est, hist = _estadia(db, fab)
    _preco(db, est)
    cupom = _cupom(db, est)
    operador = fab.usuario(role="financeiro", est=est)
    caixa = pagamento_service.abrir_caixa(db, est.id, 0.0, operador)
    pagamento_service.calcular_tarifa_estadia(db, hist.id, cupom.codigo)
    pagamento = pagamento_service.gerar_pagamento_pix(db, hist.id)

    pagamento_service.confirmar_pagamento_online(db, pagamento.id)

    db.refresh(caixa)
    db.refresh(cupom)
    db.refresh(hist)
    assert caixa.valor_pix == 6.0
    assert caixa.valor_total == 6.0
    assert caixa.quantidade_pagamentos == 1
    assert caixa.valor_descontos == 4.0
    assert cupom.usos_realizados == 1
    assert hist.status_pagamento == StatusPagamento.PAGO


def test_confirmacao_pix_nao_duplica_ticket_ja_pago_no_caixa(db, fab):
    est, hist = _estadia(db, fab)
    _preco(db, est)
    pagamento_service.calcular_tarifa_estadia(db, hist.id)
    pix = pagamento_service.gerar_pagamento_pix(db, hist.id)
    pagamento_service.registrar_pagamento(db, hist.id, "dinheiro", 10.0)

    with pytest.raises(HTTPException) as exc:
        pagamento_service.confirmar_pagamento_online(db, pix.id)
    assert exc.value.status_code == 400


def test_recalcular_sem_cupom_remove_cupom_anterior(db, fab):
    est, hist = _estadia(db, fab)
    _preco(db, est)
    cupom = _cupom(db, est)
    pagamento_service.calcular_tarifa_estadia(db, hist.id, cupom.codigo)

    pagamento_service.calcular_tarifa_estadia(db, hist.id)

    db.refresh(hist)
    assert hist.cupom_aplicado is None
    assert hist.valor_total == 10.0


def test_admin_nao_remove_vinculo_obrigatorio_de_gestor(client, db, fab):
    est = fab.est()
    gestor = fab.usuario(role="gestor", est=est)

    resposta = client.put(
        f"/api/admin/usuarios/{gestor.id}",
        json={"estacionamento_id": None},
        headers=_admin_headers(db),
    )

    assert resposta.status_code == 400
    db.refresh(gestor)
    assert gestor.estacionamento_id == est.id


def test_andar_e_vaga_nao_aceitam_identificadores_duplicados(client, db, fab):
    est = fab.est()
    andar = fab.andar(est, numero=7)
    headers = _admin_headers(db)

    andar_duplicado = client.post(
        "/api/admin/andares",
        json={"estacionamento_id": est.id, "numero_andar": 7, "capacidade": 2},
        headers=headers,
    )
    assert andar_duplicado.status_code == 409

    codigo = f"Q{uuid.uuid4().hex[:6].upper()}"
    payload = {"andar_id": andar.id, "codigo": codigo, "tipo": "comum"}
    primeira = client.post("/api/admin/vagas", json=payload, headers=headers)
    assert primeira.status_code == 201, primeira.text
    duplicada = client.post("/api/admin/vagas", json=payload, headers=headers)
    assert duplicada.status_code == 409
