"""Auditoria transacional de atividades da V1 (não grava tentativas recusadas)."""

from datetime import timezone

from sqlalchemy.orm import Session

from core.timeutils import normalizar
from models.db_models import Andar, EventoOperacional, Usuario, Vaga


def registrar_evento(
    db: Session,
    *,
    estacionamento_id: str,
    evento: str,
    usuario_id: str | None = None,
    reserva_id: str | None = None,
    vaga_id: str | None = None,
    historico_id: str | None = None,
    pagamento_id: str | None = None,
    origem: str = "sistema",
    valor: float | None = None,
) -> None:
    """Adiciona o evento na MESMA transação da alteração; quem chamou dá commit."""
    from rules.notificacoes_service import ao_evento_operacional

    ao_evento_operacional(
        db, evento=evento, usuario_id=usuario_id,
        estacionamento_id=estacionamento_id, reserva_id=reserva_id,
        vaga_id=vaga_id, pagamento_id=pagamento_id,
    )
    db.add(EventoOperacional(
        estacionamento_id=estacionamento_id,
        usuario_id=usuario_id,
        reserva_id=reserva_id,
        vaga_id=vaga_id,
        historico_id=historico_id,
        pagamento_id=pagamento_id,
        evento=evento,
        origem=origem,
        valor=valor,
    ))


def _iso_utc(dt) -> str | None:
    if dt is None:
        return None
    return normalizar(dt).replace(tzinfo=timezone.utc).isoformat()


def listar_atividades(
    db: Session,
    estacionamento_id: str | None,
    *,
    limite: int = 20,
    offset: int = 0,
    inicio=None,
    fim=None,
) -> list[dict]:
    """Ações registradas, autorizadas exclusivamente pelo escopo do endpoint."""
    limite = max(1, min(limite, 100))
    offset = max(0, offset)
    # Eventos internos usados para acompanhar vagas não poluem o histórico
    # operacional visível nem deslocam a paginação de reservas/pagamentos.
    q = db.query(EventoOperacional).filter(
        EventoOperacional.evento != "vaga_liberada"
    )
    if estacionamento_id:
        q = q.filter(EventoOperacional.estacionamento_id == estacionamento_id)
    if inicio is not None:
        q = q.filter(EventoOperacional.criado_em >= inicio)
    if fim is not None:
        q = q.filter(EventoOperacional.criado_em < fim)
    eventos = q.order_by(EventoOperacional.criado_em.desc(), EventoOperacional.id.desc()).offset(offset).limit(limite).all()
    usuarios = dict(db.query(Usuario.id, Usuario.nome).filter(
        Usuario.id.in_({e.usuario_id for e in eventos if e.usuario_id})
    ).all()) if any(e.usuario_id for e in eventos) else {}
    codigos = {
        vid: (codigo, andar)
        for vid, codigo, andar in db.query(Vaga.id, Vaga.codigo, Andar.numero_andar)
        .join(Andar, Vaga.andar_id == Andar.id)
        .filter(Vaga.id.in_({e.vaga_id for e in eventos if e.vaga_id}))
        .all()
    } if any(e.vaga_id for e in eventos) else {}
    retorno = []
    for e in eventos:
        codigo, andar = codigos.get(e.vaga_id, ("—", None))
        retorno.append({
            "id": e.id,
            "estacionamento_id": e.estacionamento_id,
            "usuario_id": e.usuario_id,
            "usuario_nome": usuarios.get(e.usuario_id) if e.usuario_id else None,
            "reserva_id": e.reserva_id,
            "pagamento_id": e.pagamento_id,
            "vaga_codigo": codigo,
            "andar_numero": andar,
            "evento": e.evento,
            "origem": e.origem,
            "valor": e.valor,
            "momento": _iso_utc(e.criado_em),
        })
    return retorno


def resumo_atividades(db: Session, estacionamento_id: str | None, inicio, fim) -> dict:
    """Contagens reais do período, sem inferir faturamento a partir de reservas."""
    from sqlalchemy import func

    q = db.query(EventoOperacional.evento, func.count(EventoOperacional.id))
    if estacionamento_id:
        q = q.filter(EventoOperacional.estacionamento_id == estacionamento_id)
    dados = dict(q.filter(
        EventoOperacional.criado_em >= inicio,
        EventoOperacional.criado_em < fim,
    ).group_by(EventoOperacional.evento).all())
    return {
        "reservas_criadas": dados.get("reserva_criada", 0),
        "reservas_canceladas": dados.get("reserva_cancelada", 0),
        "reservas_expiradas": dados.get("reserva_expirada", 0),
        "checkins": dados.get("reserva_concluida", 0),
        "pagamentos_confirmados": dados.get("pagamento_confirmado", 0),
    }
