"""API pessoal da central V1. Todo usuario_id vem do JWT, nunca do cliente."""
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.deps import get_usuario_autenticado
from core.timeutils import utc_agora
from models.database import get_db
from models.db_models import (
    AcompanhamentoVaga, Andar, DispositivoNotificacao, EntregaNotificacao,
    Estacionamento, Notificacao, Usuario,
)
from rules import notificacoes_service as service

router = APIRouter(prefix="/api/notificacoes", tags=["Notificações V1"])


class PreferenciasInput(BaseModel):
    push_ativo: bool = False
    reservas: bool = True
    lembretes: bool = True
    vagas: bool = False
    financeiro: bool = True
    resumo_diario: bool = True
    silencio_inicio: int = Field(22, ge=0, le=23)
    silencio_fim: int = Field(8, ge=0, le=23)


class DispositivoInput(BaseModel):
    token: str = Field(min_length=16, max_length=350)
    plataforma: Literal["android", "ios"]


class AcompanhamentoInput(BaseModel):
    estacionamento_id: str = Field(min_length=1, max_length=80)
    andar_id: str | None = Field(None, max_length=80)
    tipo_vaga: Literal["comum"] = "comum"


def _serialize(n: Notificacao) -> dict:
    from core.timeutils import normalizar
    from datetime import timezone

    def iso(dt):
        return normalizar(dt).replace(tzinfo=timezone.utc).isoformat() if dt else None

    return {
        "id": n.id, "tipo": n.tipo, "titulo": n.titulo,
        "mensagem": n.mensagem, "estacionamento_id": n.estacionamento_id,
        "destino": n.destino, "referencia_tipo": n.referencia_tipo,
        "referencia_id": n.referencia_id, "criada_em": iso(n.criada_em),
        "lida_em": iso(n.lida_em), "expira_em": iso(n.expira_em),
    }


@router.get("")
def listar(minhas: Literal["todas", "nao_lidas"] = "todas",
           limite: int = Query(30, ge=1, le=100),
           offset: int = Query(0, ge=0),
           db: Session = Depends(get_db),
           usuario: Usuario = Depends(get_usuario_autenticado)):
    q = db.query(Notificacao).filter(Notificacao.usuario_id == usuario.id)
    if minhas == "nao_lidas":
        q = q.filter(Notificacao.lida_em.is_(None))
    return [_serialize(n) for n in q.order_by(
        Notificacao.criada_em.desc(), Notificacao.id.desc()
    ).offset(offset).limit(limite).all()]


@router.get("/contador")
def contador(db: Session = Depends(get_db),
             usuario: Usuario = Depends(get_usuario_autenticado)):
    total = db.query(func.count(Notificacao.id)).filter(
        Notificacao.usuario_id == usuario.id, Notificacao.lida_em.is_(None)
    ).scalar() or 0
    return {"nao_lidas": total}


@router.patch("/ler-todas")
def ler_todas(db: Session = Depends(get_db),
              usuario: Usuario = Depends(get_usuario_autenticado)):
    count = db.query(Notificacao).filter(
        Notificacao.usuario_id == usuario.id, Notificacao.lida_em.is_(None)
    ).update({Notificacao.lida_em: utc_agora()}, synchronize_session=False)
    db.commit()
    return {"atualizadas": count}


@router.patch("/{notificacao_id}/ler")
def ler(notificacao_id: str, db: Session = Depends(get_db),
        usuario: Usuario = Depends(get_usuario_autenticado)):
    n = db.query(Notificacao).filter(
        Notificacao.id == notificacao_id, Notificacao.usuario_id == usuario.id
    ).first()
    if not n:
        raise HTTPException(404, "Notificação não encontrada")
    if not n.lida_em:
        n.lida_em = utc_agora()
        db.commit()
    return {"ok": True}


@router.get("/preferencias")
def obter_preferencias(db: Session = Depends(get_db),
                       usuario: Usuario = Depends(get_usuario_autenticado)):
    p = service.preferencias(db, usuario.id)
    db.commit()
    return {k: getattr(p, k) for k in (
        "push_ativo", "reservas", "lembretes", "vagas", "financeiro",
        "resumo_diario", "silencio_inicio", "silencio_fim",
    )}


@router.put("/preferencias")
def atualizar_preferencias(dados: PreferenciasInput,
                           db: Session = Depends(get_db),
                           usuario: Usuario = Depends(get_usuario_autenticado)):
    p = service.preferencias(db, usuario.id)
    for k, v in dados.model_dump().items():
        setattr(p, k, v)
    p.atualizado_em = utc_agora()
    db.commit()
    return {"ok": True}


@router.get("/push/status")
def diagnostico_push(db: Session = Depends(get_db),
                     usuario: Usuario = Depends(get_usuario_autenticado)):
    """Diagnóstico seguro para a conta atual, sem vazar tokens nem credenciais.

    'pronto' significa servidor apto a REGISTRAR e PROCESSAR entregas.
    A entrega ao celular ainda depende do build EAS, FCM/APNs e do provedor.
    """
    from rules.notificacoes_worker import _habilitado

    habilitado = _habilitado()
    try:
        service._fernet()
        criptografia = True
    except RuntimeError:
        criptografia = False

    dispositivos = db.query(func.count(DispositivoNotificacao.id)).filter(
        DispositivoNotificacao.usuario_id == usuario.id,
        DispositivoNotificacao.ativo.is_(True),
    ).scalar() or 0
    motivos = []
    if not habilitado:
        motivos.append("O envio push do servidor está desligado (NOTIFICACOES_PUSH_ENABLED).")
    if not criptografia:
        motivos.append("A chave privada de dispositivos não está configurada ou é inválida.")
    return {
        "envio_habilitado": habilitado,
        "criptografia_configurada": criptografia,
        "dispositivos_ativos": dispositivos,
        "pronto": habilitado and criptografia,
        "motivos": motivos,
    }


@router.post("/dispositivos", status_code=201)
def registrar_dispositivo(dados: DispositivoInput,
                          db: Session = Depends(get_db),
                          usuario: Usuario = Depends(get_usuario_autenticado)):
    if not re.fullmatch(r"(Expo(nent)?PushToken)\[[A-Za-z0-9_-]+\]", dados.token):
        raise HTTPException(422, "Token Expo inválido")
    import hashlib

    digest = hashlib.sha256(dados.token.encode()).hexdigest()
    atual = db.query(DispositivoNotificacao).filter_by(token_hash=digest).first()
    if atual and atual.usuario_id != usuario.id:
        # Não entregar mensagens da conta anterior após trocar de login.
        db.query(EntregaNotificacao).filter(
            EntregaNotificacao.dispositivo_id == atual.id,
            EntregaNotificacao.status == "pendente",
        ).update({EntregaNotificacao.status: "cancelada"}, synchronize_session=False)
    try:
        dispositivo = service.registrar_dispositivo(db, usuario.id, dados.token, dados.plataforma)
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(503, "Push indisponível: credenciais privadas não configuradas") from exc
    db.commit()
    return {"id": dispositivo.id, "registrado": True}


@router.delete("/dispositivos/{id}", status_code=204)
def remover_dispositivo(id: str, db: Session = Depends(get_db),
                       usuario: Usuario = Depends(get_usuario_autenticado)):
    dispositivo = db.query(DispositivoNotificacao).filter(
        DispositivoNotificacao.id == id, DispositivoNotificacao.usuario_id == usuario.id
    ).first()
    if not dispositivo:
        raise HTTPException(404, "Dispositivo não encontrado")
    dispositivo.ativo = False
    db.query(EntregaNotificacao).filter(
        EntregaNotificacao.dispositivo_id == id,
        EntregaNotificacao.status == "pendente",
    ).update({EntregaNotificacao.status: "cancelada"}, synchronize_session=False)
    db.commit()


@router.get("/acompanhamentos")
def listar_acompanhamentos(db: Session = Depends(get_db),
                           usuario: Usuario = Depends(get_usuario_autenticado)):
    return [{
        "id": w.id, "estacionamento_id": w.estacionamento_id,
        "andar_id": w.andar_id, "tipo_vaga": w.tipo_vaga, "ativo": w.ativo,
    } for w in db.query(AcompanhamentoVaga).filter_by(usuario_id=usuario.id, ativo=True).all()]


@router.post("/acompanhamentos", status_code=201)
def criar_acompanhamento(dados: AcompanhamentoInput,
                        db: Session = Depends(get_db),
                        usuario: Usuario = Depends(get_usuario_autenticado)):
    if not db.get(Estacionamento, dados.estacionamento_id):
        raise HTTPException(404, "Estacionamento não encontrado")
    if dados.andar_id:
        andar = db.get(Andar, dados.andar_id)
        if not andar or andar.estacionamento_id != dados.estacionamento_id:
            raise HTTPException(422, "Andar não pertence a este estacionamento")
    existentes = db.query(AcompanhamentoVaga).filter_by(
        usuario_id=usuario.id, ativo=True
    ).all()
    for w in existentes:
        if (w.estacionamento_id, w.andar_id, w.tipo_vaga) == (
            dados.estacionamento_id, dados.andar_id, dados.tipo_vaga,
        ):
            return {"id": w.id, "ativo": True}
    if len(existentes) >= 10:
        raise HTTPException(429, "Limite de dez acompanhamentos por conta")
    w = AcompanhamentoVaga(usuario_id=usuario.id, **dados.model_dump())
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "ativo": True}


@router.delete("/acompanhamentos/{id}", status_code=204)
def remover_acompanhamento(id: str, db: Session = Depends(get_db),
                           usuario: Usuario = Depends(get_usuario_autenticado)):
    w = db.query(AcompanhamentoVaga).filter_by(id=id, usuario_id=usuario.id).first()
    if not w:
        raise HTTPException(404, "Acompanhamento não encontrado")
    w.ativo = False
    db.commit()
