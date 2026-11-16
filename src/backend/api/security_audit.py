"""Consulta controlada da auditoria e contenção de sessões comprometidas.

Nenhuma alteração de papéis é efetuada por estas rotas.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.deps import get_usuario_admin, get_usuario_painel
from core.escopo import ids_permitidos
from core.security_audit import MAX_EVENTS_IN_QUERY, registrar_evento
from models.database import get_db
from models.db_models import EventoSeguranca, RevogacaoToken, SessaoAcesso, TipoUsuario, Usuario

router = APIRouter(prefix="/api/admin/seguranca", tags=["Auditoria de segurança"])


@router.get("/eventos")
def listar_eventos(
    limite: int = Query(50, ge=1, le=MAX_EVENTS_IN_QUERY),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_painel),
):
    """Admin vê eventos globais; equipe só eventos do próprio usuário/escopo."""
    query = db.query(EventoSeguranca)
    if usuario.role != TipoUsuario.ADMIN.value:
        from sqlalchemy import or_
        permitidos = ids_permitidos(usuario) or set()
        query = query.filter(or_(
            EventoSeguranca.usuario_id == usuario.id,
            EventoSeguranca.estacionamento_id.in_(list(permitidos)),
        ))
    eventos = query.order_by(EventoSeguranca.criado_em.desc()).limit(limite).all()
    return [{
        "id": ev.id, "usuario_id": ev.usuario_id,
        "estacionamento_id": ev.estacionamento_id,
        "categoria": ev.categoria, "operacao": ev.operacao,
        "metodo": ev.metodo, "status_http": ev.status_http,
        "criado_em": ev.criado_em,
    } for ev in eventos]


@router.post("/usuarios/{usuario_id}/revogar-sessoes")
def revogar_sessoes_de_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    """Ação explícita e auditada do admin para conter conta comprometida."""
    alvo = db.get(Usuario, usuario_id)
    if alvo is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    agora = datetime.now(timezone.utc)
    n = db.query(SessaoAcesso).filter(
        SessaoAcesso.usuario_id == usuario_id,
        SessaoAcesso.revogada_em.is_(None),
    ).update({"revogada_em": agora}, synchronize_session=False)
    db.add(RevogacaoToken(
        jti=None, usuario_id=usuario_id,
        motivo="resposta_incidente_admin", criado_em=agora,
    ))
    db.commit()
    registrar_evento(
        db, usuario_id=admin.id, categoria="resposta_incidente",
        operacao="/api/admin/seguranca/usuarios/{id}/revogar-sessoes",
        metodo="POST", status_http=200,
        estacionamento_id=alvo.estacionamento_id,
    )
    return {"usuario_id": usuario_id, "sessoes_revogadas": n,
            "mensagem": "Sessões revogadas; nenhuma permissão foi alterada"}
