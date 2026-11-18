"""Worker V1: agendamento e entrega Expo, sem bloquear operações de negócio."""
import logging
import os
from datetime import timedelta

import httpx
from sqlalchemy import or_

from core.timeutils import utc_agora, normalizar
from models.database import SessionLocal
from models.db_models import (
    DispositivoNotificacao, EntregaNotificacao, Notificacao,
    PreferenciaNotificacao, Reserva, StatusReserva, Usuario, Vaga,
)
from rules import notificacoes_service as service

LOG = logging.getLogger("smartparking.notificacoes")
PUSH_SEND = "https://exp.host/--/api/v2/push/send"
PUSH_RECEIPTS = "https://exp.host/--/api/v2/push/getReceipts"


def _habilitado() -> bool:
    return os.environ.get("NOTIFICACOES_PUSH_ENABLED", "false").lower() == "true"


def _headers() -> dict:
    token = os.environ.get("EXPO_ACCESS_TOKEN", "")
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _vivo(db, entrega: EntregaNotificacao) -> bool:
    notificacao = db.get(Notificacao, entrega.notificacao_id)
    dispositivo = db.get(DispositivoNotificacao, entrega.dispositivo_id)
    if not notificacao or not dispositivo or not dispositivo.ativo:
        return False
    if notificacao.usuario_id != dispositivo.usuario_id:
        return False
    usuario = db.get(Usuario, dispositivo.usuario_id)
    if not usuario or not usuario.is_ativo:
        return False
    p = service.preferencias(db, usuario.id)
    if not service._push_autorizado(p, notificacao.tipo):
        return False
    if notificacao.expira_em and normalizar(notificacao.expira_em) <= utc_agora():
        return False
    if notificacao.tipo == "lembrete_reserva":
        reserva = db.get(Reserva, notificacao.referencia_id)
        if not reserva or reserva.status != StatusReserva.CONFIRMADA:
            return False
    if notificacao.tipo == "vaga_disponivel":
        vaga = db.get(Vaga, notificacao.referencia_id)
        if not vaga or vaga.status != "livre":
            return False
    return True


def _claim(db):
    agora = utc_agora()
    # Um envio preso por queda de processo pode voltar para a fila após o lease.
    q = db.query(EntregaNotificacao).filter(
        EntregaNotificacao.tentativas < 5,
        EntregaNotificacao.executar_em <= agora,
        EntregaNotificacao.status.in_(["pendente", "enviando"]),
    ).order_by(EntregaNotificacao.executar_em, EntregaNotificacao.id)
    if db.bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    e = q.first()
    if not e:
        return None
    if not _vivo(db, e):
        e.status = "cancelada"
        db.commit()
        return None
    e.status = "enviando"
    e.tentativas += 1
    e.executar_em = agora + timedelta(minutes=3)
    uid = e.id
    db.commit()
    return uid


def _registrar_erro(db, entrega, message: str):
    entrega.ultimo_erro = message[:200]
    if entrega.tentativas >= 5:
        entrega.status = "falhou"
    else:
        entrega.status = "pendente"
        entrega.executar_em = utc_agora() + timedelta(seconds=min(1800, 30 * (2 ** (entrega.tentativas - 1))))


def enviar_pendentes(limite=20) -> int:
    if not _habilitado():
        return 0
    enviados = 0
    for _ in range(limite):
        db = SessionLocal()
        try:
            uid = _claim(db)
            if not uid:
                break
            e = db.get(EntregaNotificacao, uid)
            if not e or not _vivo(db, e):
                if e:
                    e.status = "cancelada"
                    db.commit()
                continue
            n = db.get(Notificacao, e.notificacao_id)
            d = db.get(DispositivoNotificacao, e.dispositivo_id)
            token = service._fernet().decrypt(d.token_expo.encode()).decode()
            # Push leva o mínimo de dados. Os detalhes financeiros ficam na API.
            push_body = n.mensagem if n.tipo not in {"resumo_financeiro", "caixa_fechado", "pagamento_confirmado"} else "Consulte o Smart Parking para ver os detalhes."
            data = {"to": token, "title": n.titulo, "body": push_body,
                    "data": {"notificacao_id": n.id, "destino": n.destino or "/notificacoes"},
                    "sound": "default", "priority": "default",
                    "channelId": "reservas" if n.tipo.startswith(("reserva_", "lembrete_")) else
                                 "vagas" if n.tipo == "vaga_disponivel" else "financeiro"}
            try:
                with httpx.Client(timeout=8) as client:
                    response = client.post(PUSH_SEND, json=data, headers=_headers())
                    response.raise_for_status()
                    resposta = response.json().get("data", {})
                if resposta.get("status") == "ok" and resposta.get("id"):
                    e.status = "aceito"
                    e.ticket_id = resposta["id"]
                    enviados += 1
                else:
                    erro = resposta.get("details", {}).get("error") or resposta.get("message", "Resposta inesperada Expo")
                    if erro == "DeviceNotRegistered":
                        d.ativo = False
                        e.status = "cancelada"
                    else:
                        _registrar_erro(db, e, str(erro))
            except (httpx.HTTPError, ValueError) as exc:
                _registrar_erro(db, e, type(exc).__name__)
            db.commit()
        except Exception:
            db.rollback()
            LOG.exception("Falha no processamento de entrega push")
        finally:
            db.close()
    return enviados


def processar_recibos():
    if not _habilitado():
        return
    db = SessionLocal()
    try:
        # No máximo 100 recibos por ciclo. Aceito pelo Expo != entregue no aparelho.
        entregas = db.query(EntregaNotificacao).filter(
            EntregaNotificacao.status == "aceito",
            EntregaNotificacao.ticket_id.isnot(None),
        ).limit(100).all()
        if not entregas:
            return
        ids = [e.ticket_id for e in entregas]
        with httpx.Client(timeout=8) as client:
            r = client.post(PUSH_RECEIPTS, json={"ids": ids}, headers=_headers())
            r.raise_for_status()
            respostas = r.json().get("data", {})
        for e in entregas:
            resultado = respostas.get(e.ticket_id)
            if not resultado:
                continue
            if resultado.get("status") == "ok":
                e.status = "confirmado_provedor"
            elif resultado.get("status") == "error":
                motivo = resultado.get("details", {}).get("error") or resultado.get("message", "Erro Expo")
                e.ultimo_erro = str(motivo)[:200]
                e.status = "falhou"
                if motivo == "DeviceNotRegistered":
                    d = db.get(DispositivoNotificacao, e.dispositivo_id)
                    if d:
                        d.ativo = False
        db.commit()
    except Exception:
        db.rollback()
        LOG.exception("Falha consultando recibos de entrega")
    finally:
        db.close()


def executar_rotina(*, gerar_resumo=False):
    """Chamado em thread, uma sessão por ciclo; falha não afeta FastAPI."""
    db = SessionLocal()
    try:
        service.lembretes_pendentes(db)
        service.disponibilidade_pendente(db)
        if gerar_resumo:
            service.resumos_diarios(db)
        db.commit()
    except Exception:
        db.rollback()
        LOG.exception("Falha na geração de notificações")
    finally:
        db.close()
    enviar_pendentes()
    processar_recibos()
