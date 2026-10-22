from datetime import datetime, time, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.timeutils import FUSO_MANAUS, janela_manaus, normalizar
from models.db_models import Historico, Vaga, StatusVaga, Estacionamento, Andar

# Dia local de referência (Manaus) para a UI exibir em qual dia o "hoje" bate
FUSO_REPORT = "America/Manaus"
_UTC = timezone.utc


def _calcular_periodo(periodo: str) -> tuple[datetime, datetime]:
    """
    Janela [início, fim) do período no calendário de Manaus (RN-12/ADR-05).
    Limites em naive-UTC — compatíveis com as colunas gravadas via
    core.timeutils.utc_agora() tanto em SQLite quanto em Postgres.
    """
    try:
        return janela_manaus(periodo)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Período inválido. Use: diario, semanal ou mensal"
        )


def _vagas_ativas_ids(db: Session, andar_id: str) -> list[str]:
    """Vagas ATIVAS do andar (inativas fora — RN-10/ACH-18)."""
    return [
        v.id for v in db.query(Vaga.id).filter(
            Vaga.andar_id == andar_id, Vaga.status != StatusVaga.INATIVA
        ).all()
    ]


def _vagas_ativas_por_andar(db: Session, andar_id: str) -> int:
    """
    Denominador de ocupação: só vagas ativas. Vagas `inativa` (interditadas)
    entravam antes no denominador e derrubavam a taxa artificialmente.
    """
    return (
        db.query(Vaga)
        .filter(Vaga.andar_id == andar_id, Vaga.status != StatusVaga.INATIVA)
        .count()
    )


def gerar_relatorio_fluxo(
    db: Session,
    periodo: str,
    estacionamento_id: Optional[str] = None
) -> dict:
    """Gera relatório de entradas e saídas no período solicitado"""
    data_inicio, data_fim = _calcular_periodo(periodo)

    query = db.query(Historico).filter(
        Historico.entrada_em >= data_inicio,
        Historico.entrada_em < data_fim
    )

    if estacionamento_id:
        query = query.filter(Historico.estacionamento_id == estacionamento_id)

    registros = query.all()

    total_entradas = len(registros)
    total_saidas = sum(1 for r in registros if r.saida_em is not None)

    tempos_permanencia = [
        r.tempo_permanencia_minutos
        for r in registros
        if r.tempo_permanencia_minutos is not None
    ]
    tempo_medio = sum(tempos_permanencia) / len(tempos_permanencia) if tempos_permanencia else 0.0

    return {
        "periodo": periodo,
        "estacionamento_id": estacionamento_id,
        "fuso": FUSO_REPORT,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "tempo_medio_permanencia_min": round(tempo_medio, 2),
        "registros": [
            {
                "id": r.id,
                "estacionamento_id": r.estacionamento_id,
                "vaga_id": r.vaga_id,
                "placa": r.placa_veiculo,
                "entrada_em": r.entrada_em,
                "saida_em": r.saida_em,
                "tempo_permanencia": r.tempo_permanencia_minutos,
                "valor_total": r.valor_total
            } for r in registros
        ]
    }


def gerar_relatorio_ocupacao(
    db: Session,
    periodo: str,
    estacionamento_id: Optional[str] = None
) -> dict:
    """Taxa de ocupação atual por andar (snapshot), com inativas fora do denominador."""
    _calcular_periodo(periodo)  # valida o período mesmo sendo snapshot

    if estacionamento_id:
        estacionamentos = db.query(Estacionamento).filter(
            Estacionamento.id == estacionamento_id
        ).all()
    else:
        estacionamentos = db.query(Estacionamento).all()

    if not estacionamentos:
        return {
            "periodo": periodo,
            "estacionamento_id": estacionamento_id,
            "fuso": FUSO_REPORT,
            "taxa_ocupacao_media": 0.0,
            "total_vagas": 0,
            "vagas_ocupadas": 0,
            "dados_por_andar": []
        }

    dados_por_andar = []
    total_vagas = 0
    total_vagas_ocupadas = 0

    for est in estacionamentos:
        for andar in est.andares:
            vagas_andar = _vagas_ativas_por_andar(db, andar.id)
            vagas_ocupadas_andar = db.query(Vaga).filter(
                Vaga.andar_id == andar.id,
                Vaga.status.in_([StatusVaga.OCUPADA, StatusVaga.RESERVADA])
            ).count()

            taxa_andar = round((vagas_ocupadas_andar / vagas_andar) * 100, 2) if vagas_andar > 0 else 0.0

            dados_por_andar.append({
                "andar_numero": andar.numero_andar,
                "estacionamento_id": est.id,
                "total_vagas": vagas_andar,
                "vagas_ocupadas": vagas_ocupadas_andar,
                "taxa_ocupacao": taxa_andar
            })

            total_vagas += vagas_andar
            total_vagas_ocupadas += vagas_ocupadas_andar

    taxa_media = round((total_vagas_ocupadas / total_vagas) * 100, 2) if total_vagas > 0 else 0.0

    return {
        "periodo": periodo,
        "estacionamento_id": estacionamento_id,
        "fuso": FUSO_REPORT,
        "taxa_ocupacao_media": taxa_media,
        "total_vagas": total_vagas,
        "vagas_ocupadas": total_vagas_ocupadas,
        "dados_por_andar": dados_por_andar
    }


def _estacionamentos_alvo(db: Session, estacionamento_id: Optional[str]):
    if estacionamento_id:
        return db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).all()
    return db.query(Estacionamento).all()


def _sobreposicao_minutos(ent: datetime, sai: datetime, j0: datetime, j1: datetime) -> int:
    """Minutos de [ent, sai) ∩ [j0, j1)."""
    ini = max(ent, j0)
    fim = min(sai, j1)
    return max(0, int((fim - ini).total_seconds() // 60))


def gerar_relatorio_ocupacao_historica(
    db: Session,
    periodo: str = "semanal",
    estacionamento_id: Optional[str] = None,
) -> dict:
    """
    RF-52 (marca 3 · ADR-09): ocupação histórica em matriz hora × andar.
    Derivada da sobreposição dos intervalos do `Historico` com cada hora do
    dia LOCAL (Manaus) — sem tabela de snapshots, sem estado novo.

    `ocupacao_por_hora[h]` = % médio das vagas ativas do andar ocupado na hora
    h (média dos buckets de 60 min ao longo dos dias da janela).
    """
    data_inicio, data_fim = _calcular_periodo(periodo)

    # dias de calendário (Manaus) cobertos pela janela UTC
    ini_local = data_inicio.replace(tzinfo=_UTC).astimezone(FUSO_MANAUS)
    fim_local = (data_fim - timedelta(seconds=1)).replace(tzinfo=_UTC).astimezone(FUSO_MANAUS)
    dias = (fim_local.date() - ini_local.date()).days + 1

    estacionamentos = _estacionamentos_alvo(db, estacionamento_id)
    if not estacionamentos:
        return {
            "periodo": periodo, "estacionamento_id": estacionamento_id,
            "fuso": FUSO_REPORT, "dias": dias, "dados_por_andar": [],
        }

    dados_por_andar = []
    for est in estacionamentos:
        for andar in est.andares:
            vaga_ids = _vagas_ativas_ids(db, andar.id)
            vagas_ativas = len(vaga_ids)

            ocupacao_por_hora = [0.0] * 24
            if vagas_ativas:
                historicos = db.query(Historico).filter(
                    Historico.vaga_id.in_(vaga_ids),
                    Historico.entrada_em < data_fim,
                    (Historico.saida_em.is_(None)) | (Historico.saida_em > data_inicio),
                ).all()
                intervals = [
                    (
                        normalizar(h.entrada_em),
                        normalizar(h.saida_em) if h.saida_em else data_fim,
                    )
                    for h in historicos
                ]

                minutos_por_hora = [0] * 24
                for k in range(dias):
                    meia_noite = datetime.combine(
                        ini_local.date() + timedelta(days=k), time(0), tzinfo=FUSO_MANAUS
                    )
                    for h in range(24):
                        j0 = (meia_noite + timedelta(hours=h)).astimezone(_UTC).replace(tzinfo=None)
                        j1 = j0 + timedelta(hours=1)
                        for ent, sai in intervals:
                            minutos_por_hora[h] += _sobreposicao_minutos(ent, sai, j0, j1)

                ocupacao_por_hora = [
                    round(100.0 * m / (vagas_ativas * 60 * dias), 2) for m in minutos_por_hora
                ]

            dados_por_andar.append({
                "andar_numero": andar.numero_andar,
                "estacionamento_id": est.id,
                "vagas_ativas": vagas_ativas,
                "ocupacao_por_hora": ocupacao_por_hora,
            })

    return {
        "periodo": periodo,
        "estacionamento_id": estacionamento_id,
        "fuso": FUSO_REPORT,
        "dias": dias,
        "dados_por_andar": dados_por_andar,
    }


def gerar_relatorio_rotacao(
    db: Session,
    periodo: str = "diario",
    estacionamento_id: Optional[str] = None,
) -> dict:
    """
    RF-54 (marca 3): giro e tempo médio por andar no período.
    `giro` = entradas do período ÷ vagas ativas (veículos por vaga).
    """
    data_inicio, data_fim = _calcular_periodo(periodo)
    estacionamentos = _estacionamentos_alvo(db, estacionamento_id)

    por_andar = []
    total_entradas = 0
    tempos: list[int] = []

    for est in estacionamentos:
        for andar in est.andares:
            vaga_ids = [
                v.id for v in db.query(Vaga.id).filter(Vaga.andar_id == andar.id).all()
            ]
            registros = db.query(Historico).filter(
                Historico.vaga_id.in_(vaga_ids),
                Historico.entrada_em >= data_inicio,
                Historico.entrada_em < data_fim,
            ).all() if vaga_ids else []

            t_andar = [
                r.tempo_permanencia_minutos for r in registros
                if r.tempo_permanencia_minutos is not None
            ]
            tempos.extend(t_andar)
            total_entradas += len(registros)

            vagas_ativas = _vagas_ativas_por_andar(db, andar.id)
            por_andar.append({
                "andar_numero": andar.numero_andar,
                "estacionamento_id": est.id,
                "entradas": len(registros),
                "vagas_ativas": vagas_ativas,
                "giro": round(len(registros) / vagas_ativas, 2) if vagas_ativas else 0.0,
                "tempo_medio_min": round(sum(t_andar) / len(t_andar), 1) if t_andar else 0.0,
            })

    return {
        "periodo": periodo,
        "estacionamento_id": estacionamento_id,
        "fuso": FUSO_REPORT,
        "total_entradas": total_entradas,
        "tempo_medio_min": round(sum(tempos) / len(tempos), 1) if tempos else 0.0,
        "por_andar": sorted(por_andar, key=lambda x: (x["estacionamento_id"], x["andar_numero"])),
    }
