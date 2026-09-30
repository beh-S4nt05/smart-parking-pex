from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.db_models import Historico, Vaga, StatusVaga, Estacionamento, Andar


def _calcular_periodo(periodo: str) -> tuple[datetime, datetime]:
    """Calcula data de início e fim baseado no período solicitado"""
    hoje = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    if periodo == "diario":
        return hoje, hoje + timedelta(days=1)
    elif periodo == "semanal":
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        return inicio_semana, inicio_semana + timedelta(days=7)
    elif periodo == "mensal":
        inicio_mes = hoje.replace(day=1)
        if inicio_mes.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        return inicio_mes, fim_mes
    else:
        raise HTTPException(
            status_code=400,
            detail="Período inválido. Use: diario, semanal ou mensal"
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
    """Gera relatório de taxa de ocupação com dados por andar"""
    data_inicio, data_fim = _calcular_periodo(periodo)

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
            vagas_andar = db.query(Vaga).filter(Vaga.andar_id == andar.id).count()
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
        "taxa_ocupacao_media": taxa_media,
        "total_vagas": total_vagas,
        "vagas_ocupadas": total_vagas_ocupadas,
        "dados_por_andar": dados_por_andar
    }
