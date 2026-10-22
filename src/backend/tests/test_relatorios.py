"""Tarefas M3-01/M3-02 (ACH-01/18) e RN-10/RN-12 — fuso, denominador, heat."""

from datetime import UTC, datetime, timedelta

from core.timeutils import FUSO_MANAUS, inicio_dia_manaus, janela_manaus, utc_agora
from models.db_models import Historico, StatusVaga
from rules import relatorio_service


def test_dia_local_de_manaus_vira_0300_utc():
    # 22/10 01:00 UTC = 21/10 22:00 em Manaus → "hoje" local é dia 21
    ref = datetime(2026, 10, 22, 1, 0, tzinfo=UTC)
    inicio = inicio_dia_manaus(ref)
    assert inicio == datetime(2026, 10, 21, 3, 0)  # 21/10 00:00-03:00 → 03:00 UTC


def test_jornada_diaria_cobre_24h_e_periodo_invalido_estoura():
    ini, fim = janela_manaus("diario")
    assert fim - ini == timedelta(hours=24)
    try:
        janela_manaus("trimestral")
        raise AssertionError("deveria levantar ValueError")
    except ValueError:
        pass


def test_ocupacao_snapshot_exclui_inativas_do_denominador(db, fab):
    """RN-10/ACH-18: 4 vagas, 2 inativas, 1 ocupada → 50% (não 25%)."""
    est = fab.est()
    andar = fab.andar(est, capacidade=4)
    fab.vaga(andar, status=StatusVaga.INATIVA)
    fab.vaga(andar, status=StatusVaga.INATIVA)
    fab.vaga(andar, status=StatusVaga.OCUPADA)
    fab.vaga(andar, status=StatusVaga.LIVRE)
    db.commit()

    dados = relatorio_service.gerar_relatorio_ocupacao(db, "diario", est.id)
    andar_dado = dados["dados_por_andar"][0]
    assert andar_dado["total_vagas"] == 2
    assert andar_dado["taxa_ocupacao"] == 50.0


def test_ocupacao_historica_bucket_atual_e_cheio_e_madrugada_zerada(db, fab):
    """Estadia aberta AGORA pinta o bucket da hora local corrente (ADR-09)."""
    est = fab.est()
    andar = fab.andar(est)
    vaga = fab.vaga(andar, status=StatusVaga.OCUPADA)
    agora = utc_agora()
    db.add(
        Historico(
            estacionamento_id=est.id, vaga_id=vaga.id,
            entrada_em=agora - timedelta(minutes=45), saida_em=agora,
            tempo_permanencia_minutos=45,
        )
    )
    db.commit()

    dados = relatorio_service.gerar_relatorio_ocupacao_historica(db, "diario", est.id)
    linha = dados["dados_por_andar"][0]
    lista = linha["ocupacao_por_hora"]
    assert len(lista) == 24
    hora_local = agora.replace(tzinfo=UTC).astimezone(FUSO_MANAUS).hour
    assert lista[hora_local] > 0
    # uma estadia de 45 min pode tocar NO MÁXIMO 2 buckets (o seu e o vizinho
    # do começo da hora); todo o resto tem que estar zerado
    cheios = [i for i, v in enumerate(lista) if v > 0]
    assert len(cheios) <= 2
    assert set(cheios) <= {hora_local, (hora_local - 1) % 24}


def test_rotacao_giro_tempo_medio(db, fab):
    est = fab.est()
    andar = fab.andar(est, capacidade=2)
    v1 = fab.vaga(andar)
    v2 = fab.vaga(andar)
    agora = utc_agora()
    for vaga, mins in ((v1, 60), (v2, 30), (v1, 90)):
        db.add(
            Historico(
                estacionamento_id=est.id, vaga_id=vaga.id,
                entrada_em=agora - timedelta(minutes=mins + 5),
                saida_em=agora - timedelta(minutes=5),
                tempo_permanencia_minutos=mins,
            )
        )
    db.commit()

    dados = relatorio_service.gerar_relatorio_rotacao(db, "diario", est.id)
    assert dados["total_entradas"] == 3
    linha = dados["por_andar"][0]
    assert linha["entradas"] == 3
    assert linha["giro"] == 1.5  # 3 entradas ÷ 2 vagas ativas
    assert linha["tempo_medio_min"] == 60.0
