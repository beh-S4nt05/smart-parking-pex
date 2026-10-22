"""M3-05 (P13/P14/P16 · ACH-07) — tarifa, cupom e resumo financeiro."""

from datetime import timedelta

import pytest

from core.timeutils import utc_agora
from models.db_models import CupomDesconto, Historico, Pagamento, StatusPagamento
from rules import financeiro_service, pagamento_service


def _com_estadia(db, fab, minutos=75, tipo_vaga="comum", est=None):
    if est is None:
        est = fab.est()
    andar = fab.andar(est)
    vaga = fab.vaga(andar, tipo=tipo_vaga)
    agora = utc_agora()
    hist = Historico(
        estacionamento_id=est.id, vaga_id=vaga.id,
        entrada_em=agora - timedelta(minutes=minutos),
        saida_em=agora, tempo_permanencia_minutos=minutos,
    )
    db.add(hist); db.commit()
    return est, hist


def _preco(db, est, **kw):
    from models.db_models import ConfiguracaoPreco

    base = {
        "estacionamento_id": est.id, "tipo_vaga": "comum", "valor_hora": 10.0,
        "valor_diaria": 80.0, "tolerancia_minutos": 15,
    }
    base.update(kw)
    p = ConfiguracaoPreco(**base)
    db.add(p); db.commit()
    return p


def test_tarifa_dentro_da_tolerancia_e_zero(db, fab):
    est, hist = _com_estadia(db, fab, minutos=10)
    _preco(db, est)
    r = pagamento_service.calcular_tarifa_estadia(db, hist.id)
    assert r["valor_total"] == 0.0


def test_tarifa_por_hora_cheia(db, fab):
    est, hist = _com_estadia(db, fab, minutos=75)  # 60 cobrados após tolerância
    _preco(db, est)
    r = pagamento_service.calcular_tarifa_estadia(db, hist.id)
    assert r["valor_bruto"] == 10.0


def test_tarifa_acima_de_9h_vira_diaria(db, fab):
    est, hist = _com_estadia(db, fab, minutos=560)
    _preco(db, est)
    r = pagamento_service.calcular_tarifa_estadia(db, hist.id)
    assert r["valor_bruto"] == 80.0  # 1 diária, não 10×10


def test_tarifa_por_fracao_15min(db, fab):
    est, hist = _com_estadia(db, fab, minutos=46)
    _preco(db, est, valor_fração_15min=3.0)
    r = pagamento_service.calcular_tarifa_estadia(db, hist.id)
    # 31 min cobrados → 3 frações × 3.00 = 9.00
    assert r["valor_bruto"] == 9.0


def test_cupom_calculo_nao_consome_uso_pagamento_consome(db, fab):
    """ACH-07: o limite de usos só gasta no pagamento confirmado."""
    import uuid

    est, hist = _com_estadia(db, fab, minutos=75)
    _preco(db, est)
    cod = f"QA{uuid.uuid4().hex[:6].upper()}"
    cupom = CupomDesconto(
        estacionamento_id=est.id, codigo=cod, tipo_desconto="valor_fixo",
        valor_desconto=4.0, limite_usos=1, usos_realizados=0, ativo=True,
    )
    db.add(cupom); db.commit()

    r1 = pagamento_service.calcular_tarifa_estadia(db, hist.id, cod)
    assert r1["desconto_aplicado"] == 4.0
    assert r1["valor_total"] == 6.0
    assert cupom.usos_realizados == 0  # calcular NÃO consome
    r2 = pagamento_service.calcular_tarifa_estadia(db, hist.id, cod)
    assert r2["valor_total"] == 6.0  # ainda utilizável (limite=1 não gasto)

    pagamento_service.registrar_pagamento(db, hist.id, "dinheiro", 10.0, None, None)
    db.refresh(cupom)
    assert cupom.usos_realizados == 1  # PAGAMENTO consome

    # cupom com limite atingido: nova estadia no MESMO estacionamento é barrada
    _, hist2 = _com_estadia(db, fab, minutos=75, est=est)
    with pytest.raises(Exception) as exc:
        pagamento_service.calcular_tarifa_estadia(db, hist2.id, cod)
    assert "limite" in str(exc.value.detail).lower()


def test_resumo_soma_credito_e_debito_como_cartao(db, fab):
    """P16: o resumo somava método inexistente 'cartao' → 0 para tudo."""
    est = fab.est()
    agora = utc_agora()
    for met, valor in (("cartao_credito", 40.0), ("cartao_debito", 20.0), ("dinheiro", 15.0)):
        db.add(
            Pagamento(
                historico_id="h-" + met, estacionamento_id=est.id,
                valor_bruto=valor, valor_desconto=0.0, valor_total=valor,
                metodo_pagamento=met, status_pagamento=StatusPagamento.PAGO.value,
                data_pagamento=agora,
            )
        )
    db.commit()

    admin = fab.usuario(role="admin")
    resumo = financeiro_service.obter_resumo_financeiro(db, "diario", est.id, admin)
    assert resumo["faturamento_total"] == 75.0
    assert resumo["pagamentos_cartao"] == 2
    assert resumo["valor_cartao"] == 60.0
    assert resumo["pagamentos_dinheiro"] == 1
    assert resumo["valor_dinheiro"] == 15.0


def test_financeiro_service_sem_registrar_quebrado():
    """P13/P14: o registrar duplicado saiu de cena — só pagamento_service paga."""
    from rules import financeiro_service as fs

    assert not hasattr(fs, "registrar_pagamento")
    assert not hasattr(fs, "RegistrarPagamentoRequest")
