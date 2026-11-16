"""Elegibilidade da V1: o direito à vaga depende de credencial verificada.

Nunca inferir aprovação da data de nascimento ou de usuarios.is_pcd.
A data de nascimento pode ser usada apenas para pré-requisito do pedido
de credencial de idoso, não como substituto da comprovação oficial.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.db_models import CredencialEstacionamento


def credencial_valida(
    db: Session, usuario_id: str, tipo: str
) -> CredencialEstacionamento | None:
    if tipo not in {"pcd", "idoso"}:
        return None
    hoje = datetime.now(timezone.utc).date()
    candidatas = db.query(CredencialEstacionamento).filter(
        CredencialEstacionamento.usuario_id == usuario_id,
        CredencialEstacionamento.tipo == tipo,
        CredencialEstacionamento.status == "aprovado",
    ).order_by(CredencialEstacionamento.verificado_em.desc()).all()
    return next((c for c in candidatas if c.validade is None or c.validade >= hoje), None)
