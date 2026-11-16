"""Sessões autenticadas, inventário, rotação de refresh e revogação no servidor."""
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from core.security import criar_token, decodificar_token
from models.db_models import SessaoAcesso, Usuario


def _digest(jti: str) -> str:
    return hashlib.sha256(jti.encode("ascii")).hexdigest()


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iniciar(db: Session, usuario: Usuario, agente: str | None = None) -> tuple[str, str]:
    sessao = SessaoAcesso(
        usuario_id=usuario.id, refresh_jti_hash="",
        dispositivo=(agente or "Dispositivo desconhecido")[:160],
        expira_em=_agora() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(sessao)
    db.flush()
    acesso = criar_token(usuario.id, "access", sessao_id=sessao.id)
    refresh = criar_token(usuario.id, "refresh", sessao_id=sessao.id)
    sessao.refresh_jti_hash = _digest(decodificar_token(refresh)["jti"])
    db.commit()
    return acesso, refresh


def sessao_valida(db: Session, usuario_id: str, sessao_id: str) -> bool:
    sessao = db.get(SessaoAcesso, sessao_id)
    return bool(sessao and sessao.usuario_id == usuario_id and
                sessao.revogada_em is None and _aware(sessao.expira_em) > _agora())


def renovar(db: Session, usuario: Usuario, payload: dict) -> tuple[str, str]:
    sid = payload.get("sid")
    jti = payload.get("jti")
    if not sid or not jti:
        raise HTTPException(status_code=401, detail="Sessão sem identificador de rotação")
    sessao = db.query(SessaoAcesso).filter(
        SessaoAcesso.id == sid, SessaoAcesso.usuario_id == usuario.id,
    ).with_for_update().first()
    if not sessao or sessao.revogada_em or _aware(sessao.expira_em) <= _agora():
        raise HTTPException(status_code=401, detail="Sessão encerrada ou expirada")
    if sessao.refresh_jti_hash != _digest(jti):
        sessao.revogada_em = _agora()  # replay de refresh antigo encerra a sessão
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh reutilizado; sessão revogada")
    access = criar_token(usuario.id, "access", sessao_id=sid)
    refresh = criar_token(usuario.id, "refresh", sessao_id=sid)
    sessao.refresh_jti_hash = _digest(decodificar_token(refresh)["jti"])
    sessao.ultimo_acesso_em = _agora()
    db.commit()
    return access, refresh


def revogar(db: Session, usuario_id: str, sessao_id: str) -> None:
    sessao = db.query(SessaoAcesso).filter(
        SessaoAcesso.id == sessao_id, SessaoAcesso.usuario_id == usuario_id,
    ).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if sessao.revogada_em is None:
        sessao.revogada_em = _agora()
        db.commit()


def listar(db: Session, usuario_id: str) -> list[dict]:
    sessoes = db.query(SessaoAcesso).filter(
        SessaoAcesso.usuario_id == usuario_id
    ).order_by(SessaoAcesso.criado_em.desc()).limit(100).all()
    return [{
        "id": s.id, "dispositivo": s.dispositivo,
        "criado_em": s.criado_em, "ultimo_acesso_em": s.ultimo_acesso_em,
        "expira_em": s.expira_em,
        "ativa": bool(s.revogada_em is None and _aware(s.expira_em) > _agora()),
    } for s in sessoes]
