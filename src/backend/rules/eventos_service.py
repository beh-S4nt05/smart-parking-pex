
from sqlalchemy.orm import Session

from models.db_models import Andar, Historico, Vaga


def listar_eventos_recentes(
    db: Session,
    estacionamento_id: str | None = None,
    limite: int = 8,
) -> list[dict]:
    """
    Feed de "Últimos eventos de vagas" para o dashboard do painel:
    cruza histórico de entradas/saídas com o status atual da vaga e
    classifica a origem (sensor, simulador QR, app do motorista).
    """
    query = db.query(Historico).join(Vaga, Historico.vaga_id == Vaga.id)
    if estacionamento_id:
        query = query.filter(Historico.estacionamento_id == estacionamento_id)

    registros = (
        query.order_by(Historico.entrada_em.desc())
        .limit(limite * 2)  # filtro leve de duplicatas de saída
        .all()
    )

    eventos: list[dict] = []
    vistos = set()
    for h in registros:
        chave = (h.vaga_id, h.entrada_em)
        if chave in vistos:
            continue
        vistos.add(chave)

        andar_numero = h.vaga.andar.numero_andar if h.vaga and h.vaga.andar else None
        momento = h.saida_em or h.entrada_em
        tipo_evento = "saida" if h.saida_em else ("entrada")
        if h.vaga:
            if h.vaga.status == "reservada" and h.saida_em is None:
                tipo_evento = "reserva"
            elif h.saida_em and h.valor_total:
                tipo_evento = "saida"
            else:
                tipo_evento = "entrada"

        eventos.append(
            {
                "id": h.id,
                "vaga_codigo": h.vaga.codigo if h.vaga else "—",
                "vaga_status": h.vaga.status if h.vaga else "inativa",
                "andar_numero": andar_numero,
                "origem": h.origem or ("app_motorista" if h.usuario_id else "sensor"),
                "evento": tipo_evento,
                "momento": momento.isoformat() if momento else None,
            }
        )
        if len(eventos) >= limite:
            break

    return eventos


def ocupacao_por_andar(db: Session, estacionamento_id: str) -> list[dict]:
    """Percentual de ocupação por andar — usado nas barras do dashboard."""
    andares = (
        db.query(Andar)
        .filter(Andar.estacionamento_id == estacionamento_id)
        .order_by(Andar.numero_andar)
        .all()
    )
    resultado = []
    for andar in andares:
        total = db.query(Vaga).filter(Vaga.andar_id == andar.id).count()
        ocupadas = (
            db.query(Vaga)
            .filter(
                Vaga.andar_id == andar.id,
                Vaga.status.in_(["ocupada", "reservada"]),
            )
            .count()
        )
        resultado.append(
            {
                "andar_id": andar.id,
                "numero_andar": andar.numero_andar,
                "total_vagas": total,
                "ocupadas": ocupadas,
                "livres": total - ocupadas,
                "percentual": round((ocupadas / total) * 100) if total else 0,
            }
        )
    return resultado
