"""Feed operacional do painel: reservas, cancelamentos, pagamentos e vagas."""

from datetime import timezone
from sqlalchemy.orm import Session

from core.timeutils import normalizar
from models.db_models import Andar, Historico, Vaga
from rules.atividade_service import listar_atividades


def listar_eventos_recentes(
    db: Session,
    estacionamento_id: str | None = None,
    limite: int = 8,
) -> list[dict]:
    """Intercala eventos auditáveis e movimentações físicas, em ordem temporal.

    A autorização de estacionamento é aplicada pela rota /api/admin/eventos.
    """
    limite = max(1, min(limite, 50))
    atividades = listar_atividades(db, estacionamento_id, limite=limite * 2)
    ids_vagas = {a["vaga_codigo"] for a in atividades}
    query = db.query(Historico).join(Vaga, Historico.vaga_id == Vaga.id)
    if estacionamento_id:
        query = query.filter(Historico.estacionamento_id == estacionamento_id)
    historicos = query.order_by(Historico.entrada_em.desc()).limit(limite * 3).all()
    eventos = []
    for h in historicos:
        if not h.vaga:
            continue
        base = {
            "id": "hist-" + h.id,
            "vaga_codigo": h.vaga.codigo,
            "vaga_status": h.vaga.status,
            "andar_numero": h.vaga.andar.numero_andar if h.vaga.andar else None,
            "origem": h.origem or ("app_motorista" if h.usuario_id else "sensor"),
            "usuario_id": h.usuario_id,
            "usuario_nome": h.usuario.nome if h.usuario else None,
            "reserva_id": None,
            "valor": h.valor_total,
        }
        if h.saida_em:
            eventos.append({
                **base, "evento": "saida", "momento":
                normalizar(h.saida_em).replace(tzinfo=timezone.utc).isoformat()
            })
        eventos.append({
            **base, "id": "entrada-" + h.id, "evento": "entrada",
            "momento": normalizar(h.entrada_em).replace(tzinfo=timezone.utc).isoformat(),
        })

    # O feed operacional é append-only, portanto eventos de reserva cancelada
    # continuam aparecendo mesmo quando a vaga já voltou a ficar livre.
    for a in atividades:
        # O status é contextual ao evento, não reclassifica o evento histórico.
        evento = a["evento"]
        status = {
            "reserva_criada": "reservada",
            "reserva_cancelada": "livre",
            "reserva_expirada": "livre",
            "reserva_concluida": "ocupada",
            "pagamento_confirmado": "livre",
        }.get(evento, "livre")
        eventos.append({**a, "id": "op-" + a["id"], "vaga_status": status})
    eventos.sort(key=lambda e: e["momento"] or "", reverse=True)
    return eventos[:limite]

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
