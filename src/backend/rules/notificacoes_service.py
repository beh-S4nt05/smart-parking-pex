"""Motor V1: notificações transacionais, lembretes, vagas e caixa.

Sem acesso externo em transações de negócio. Idempotência por chave única,
inclusive quando mais de um worker processar o mesmo evento.
"""
import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from core.config import settings
from core.timeutils import FUSO_MANAUS, normalizar, utc_agora
from models.db_models import (
    AcompanhamentoVaga, Andar, DispositivoNotificacao, EntregaNotificacao,
    Estacionamento, EventoOperacional, FechamentoCaixa, Notificacao, Pagamento,
    PreferenciaNotificacao, Reserva, StatusReserva, StatusVaga, TipoUsuario,
    Usuario, Vaga,
)

EVENTOS_RESERVA = {
    "reserva_criada": ("reserva_confirmada", "Reserva confirmada"),
    "reserva_cancelada": ("reserva_cancelada", "Reserva cancelada"),
    "reserva_expirada": ("reserva_expirada", "Reserva expirada"),
    "reserva_concluida": ("reserva_concluida", "Entrada registrada"),
    "pagamento_confirmado": ("pagamento_confirmado", "Pagamento confirmado"),
}
EVENTOS_CRITICOS = {"reserva_confirmada", "reserva_cancelada", "reserva_expirada"}
PUSH_TYPES = {"reserva_confirmada", "reserva_cancelada", "reserva_expirada", "lembrete_reserva",
              "vaga_disponivel", "pagamento_confirmado", "caixa_fechado", "resumo_financeiro"}
TIPOS_USUARIO_FINANCEIRO = (TipoUsuario.FINANCEIRO.value, TipoUsuario.ADMIN.value)


def _fernet() -> Fernet:
    # Chave independente de armazenamento, derivada da credencial do servidor.
    secret = settings.APP_SIGNING_SECRET
    if not secret or len(secret) < 16:
        raise RuntimeError("APP_SIGNING_SECRET fraco: recusar tokens push")
    raw = hashlib.sha256(("notificacoes-v1/" + secret).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def _inserir_sem_duplicar(db: Session, model, values: dict, unique: str) -> bool:
    dialect = db.bind.dialect.name
    if dialect == "postgresql":
        stmt = pg_insert(model).values(**values).on_conflict_do_nothing(index_elements=[unique])
    elif dialect == "sqlite":
        stmt = sqlite_insert(model).values(**values).on_conflict_do_nothing(index_elements=[unique])
    else:
        raise RuntimeError("Notificações requerem PostgreSQL ou SQLite de teste")
    return db.execute(stmt).rowcount == 1


def preferencias(db: Session, usuario_id: str) -> PreferenciaNotificacao:
    pref = db.get(PreferenciaNotificacao, usuario_id)
    if not pref:
        pref = PreferenciaNotificacao(usuario_id=usuario_id)
        db.add(pref)
        db.flush()
    return pref


def _push_autorizado(pref: PreferenciaNotificacao, tipo: str) -> bool:
    if not pref.push_ativo or tipo not in PUSH_TYPES:
        return False
    if tipo in {"reserva_confirmada", "reserva_cancelada", "reserva_expirada"}:
        return pref.reservas
    if tipo == "lembrete_reserva":
        return pref.lembretes
    if tipo == "vaga_disponivel":
        return pref.vagas
    if tipo == "resumo_financeiro":
        return pref.financeiro and pref.resumo_diario
    return pref.financeiro


def _depois_silencio(pref: PreferenciaNotificacao, now: datetime) -> datetime:
    hora_local = now.replace(tzinfo=timezone.utc).astimezone(FUSO_MANAUS)
    h = hora_local.hour
    a, b = pref.silencio_inicio, pref.silencio_fim
    dentro = (a > b and (h >= a or h < b)) or (a < b and a <= h < b)
    if not dentro:
        return now
    fim = hora_local.replace(hour=b, minute=0, second=0, microsecond=0)
    if hora_local >= fim:
        fim += timedelta(days=1)
    return normalizar(fim)


def _novo_destinatario(db: Session, usuario_id: str, tipo: str, titulo: str,
                       mensagem: str, chave: str, estacionamento_id=None,
                       destino=None, referencia_tipo=None, referencia_id=None,
                       expira_em=None) -> Notificacao | None:
    import uuid

    values = {
        "id": str(uuid.uuid4()), "usuario_id": usuario_id, "tipo": tipo,
        "titulo": titulo, "mensagem": mensagem, "destino": destino,
        "chave_idempotencia": chave, "estacionamento_id": estacionamento_id,
        "referencia_tipo": referencia_tipo, "referencia_id": referencia_id,
        "expira_em": expira_em, "criada_em": utc_agora(),
    }
    if not _inserir_sem_duplicar(db, Notificacao, values, "chave_idempotencia"):
        return None
    notificacao = db.get(Notificacao, values["id"])
    pref = preferencias(db, usuario_id)
    if _push_autorizado(pref, tipo):
        agora = utc_agora()
        agendada = _depois_silencio(pref, agora) if tipo in {"vaga_disponivel", "resumo_financeiro"} else agora
        if not expira_em or agendada < normalizar(expira_em):
            for dispositivo in db.query(DispositivoNotificacao).filter_by(usuario_id=usuario_id, ativo=True).all():
                db.add(EntregaNotificacao(
                    notificacao_id=notificacao.id, dispositivo_id=dispositivo.id,
                    status="pendente", tentativas=0, executar_em=agendada,
                    expira_em=expira_em,
                ))
    return notificacao


def ao_evento_operacional(db: Session, *, evento: str, usuario_id: str | None,
                         estacionamento_id: str, reserva_id=None, vaga_id=None,
                         pagamento_id=None):
    """Chamado antes do commit na mesma transação de reserva/pagamento."""
    if not usuario_id or evento not in EVENTOS_RESERVA:
        return
    tipo, titulo = EVENTOS_RESERVA[evento]
    vaga = db.get(Vaga, vaga_id) if vaga_id else None
    codigo = vaga.codigo if vaga else "—"
    if evento == "pagamento_confirmado":
        mensagem = "Pagamento registrado. Confira os detalhes no aplicativo."
        destino = "/reservas"
        entidade, referencia = "pagamento", pagamento_id
    else:
        mensagem = f"Vaga {codigo}: {titulo.lower()}."
        destino = "/reservas"
        entidade, referencia = "reserva", reserva_id
    chave = f"operacao:{evento}:{pagamento_id or reserva_id}"
    _novo_destinatario(db, usuario_id, tipo, titulo, mensagem, chave,
                       estacionamento_id=estacionamento_id, destino=destino,
                       referencia_tipo=entidade, referencia_id=referencia)


def registrar_dispositivo(db: Session, usuario_id: str, token: str, plataforma: str):
    digest = hashlib.sha256(token.encode()).hexdigest()
    cifrado = _fernet().encrypt(token.encode()).decode()
    registro = db.query(DispositivoNotificacao).filter_by(token_hash=digest).first()
    if not registro:
        registro = DispositivoNotificacao(usuario_id=usuario_id, token_hash=digest,
                                         token_expo=cifrado, plataforma=plataforma, ativo=True)
        db.add(registro)
    else:
        # Troca de conta no mesmo celular não pode entregar eventos de outra conta.
        registro.usuario_id = usuario_id
        registro.token_expo = cifrado
        registro.plataforma = plataforma
        registro.ativo = True
    registro.ultimo_uso_em = utc_agora()
    db.flush()
    return registro


def lembretes_pendentes(db: Session, agora: datetime | None = None) -> int:
    agora = agora or utc_agora()
    janela = agora + timedelta(minutes=15)
    reservas = db.query(Reserva).filter(
        Reserva.status == StatusReserva.CONFIRMADA,
        Reserva.horario_fim > agora,
        Reserva.horario_fim <= janela,
    ).limit(200).all()
    count = 0
    for reserva in reservas:
        pref = preferencias(db, reserva.usuario_id)
        if not pref.lembretes:
            continue
        vaga = db.get(Vaga, reserva.vaga_id)
        est_id = vaga.andar.estacionamento_id if vaga and vaga.andar else None
        mensagem = f"Sua reserva da vaga {vaga.codigo if vaga else '—'} está perto do vencimento."
        if _novo_destinatario(db, reserva.usuario_id, "lembrete_reserva", "Reserva perto do prazo",
                              mensagem, f"reserva:{reserva.id}:aviso15", estacionamento_id=est_id,
                              destino="/reservas", referencia_tipo="reserva",
                              referencia_id=reserva.id, expira_em=reserva.horario_fim):
            count += 1
    return count


def disponibilidade_pendente(db: Session, agora: datetime | None = None) -> int:
    """Emite no máximo 3 avisos/dia, com estabilização 10 s e cooldown 30 min."""
    agora = agora or utc_agora()
    inicio = agora - timedelta(minutes=5)
    eventos = db.query(EventoOperacional).filter(
        EventoOperacional.evento == "vaga_liberada",
        EventoOperacional.criado_em >= inicio,
        EventoOperacional.criado_em <= agora - timedelta(seconds=10),
    ).order_by(EventoOperacional.criado_em.desc()).limit(200).all()
    notificados = 0
    for ev in eventos:
        vaga = db.get(Vaga, ev.vaga_id) if ev.vaga_id else None
        # Vagas especiais precisam de análise de elegibilidade; não prometer.
        if not vaga or vaga.status != StatusVaga.LIVRE or vaga.tipo not in {"comum", "moto"}:
            continue
        watches = db.query(AcompanhamentoVaga).filter_by(
            estacionamento_id=ev.estacionamento_id, ativo=True).all()
        for watch in watches:
            if (watch.andar_id and watch.andar_id != vaga.andar_id) or (
                watch.tipo_vaga and watch.tipo_vaga != vaga.tipo
            ):
                continue
            pref = preferencias(db, watch.usuario_id)
            if not pref.vagas:
                continue
            user = db.get(Usuario, watch.usuario_id)
            if not user or not user.is_ativo:
                continue
            if vaga.tipo == "moto":
                # Sem validação do veículo nesse fluxo, não recomendar vaga moto.
                continue
            if watch.ultimo_aviso_em and normalizar(watch.ultimo_aviso_em) > agora - timedelta(minutes=30):
                continue
            hoje = (agora.replace(tzinfo=timezone.utc).astimezone(FUSO_MANAUS)
                    .replace(hour=0, minute=0, second=0, microsecond=0))
            inicio_dia = normalizar(hoje)
            total_hoje = db.query(Notificacao).filter(
                Notificacao.usuario_id == watch.usuario_id,
                Notificacao.tipo == "vaga_disponivel",
                Notificacao.criada_em >= inicio_dia,
            ).count()
            if total_hoje >= 3:
                continue
            notif = _novo_destinatario(
                db, watch.usuario_id, "vaga_disponivel", "Vaga disponível",
                "Uma vaga comum acompanhada está livre. Confirme no mapa antes de reservar.",
                f"vaga:{ev.id}:watch:{watch.id}", estacionamento_id=ev.estacionamento_id,
                destino=f"/shopping/{ev.estacionamento_id}", referencia_tipo="vaga",
                referencia_id=vaga.id, expira_em=agora + timedelta(minutes=3),
            )
            if notif:
                watch.ultimo_aviso_em = agora
                notificados += 1
    return notificados


def financeiro_destinatarios(db: Session, estacionamento_id: str) -> list[str]:
    return [
        u.id for u in db.query(Usuario).filter(
            Usuario.role.in_(TIPOS_USUARIO_FINANCEIRO),
            Usuario.is_ativo.is_(True),
        ).all()
        if u.role == TipoUsuario.ADMIN.value or u.estacionamento_id == estacionamento_id
    ]


def ao_fechar_caixa(db: Session, caixa: FechamentoCaixa):
    for uid in financeiro_destinatarios(db, caixa.estacionamento_id):
        _novo_destinatario(
            db, uid, "caixa_fechado", "Caixa fechado",
            "O fechamento do caixa foi registrado. Consulte os detalhes no painel.",
            f"fechamento:{caixa.id}:usuario:{uid}", estacionamento_id=caixa.estacionamento_id,
            destino="/dashboard", referencia_tipo="caixa", referencia_id=caixa.id,
        )


def resumos_diarios(db: Session, agora: datetime | None = None) -> int:
    agora = agora or utc_agora()
    local = agora.replace(tzinfo=timezone.utc).astimezone(FUSO_MANAUS)
    if local.hour < 7:
        return 0
    fim = normalizar(local.replace(hour=0, minute=0, second=0, microsecond=0))
    inicio = fim - timedelta(days=1)
    count = 0
    for est in db.query(Estacionamento).all():
        faturamento, qtd = db.query(
            func.coalesce(func.sum(Pagamento.valor_total), 0), func.count(Pagamento.id)
        ).filter(
            Pagamento.estacionamento_id == est.id,
            Pagamento.status_pagamento == "pago",
            Pagamento.data_pagamento >= inicio,
            Pagamento.data_pagamento < fim,
        ).one()
        caixas_abertos = db.query(FechamentoCaixa).filter_by(
            estacionamento_id=est.id, fechado=False).count()
        for uid in financeiro_destinatarios(db, est.id):
            pref = preferencias(db, uid)
            if not pref.financeiro or not pref.resumo_diario:
                continue
            mensagem = (f"Dia anterior: R$ {float(faturamento):.2f} em {qtd} pagamento(s). "
                        f"Caixas ainda abertos: {caixas_abertos}.")
            if _novo_destinatario(
                db, uid, "resumo_financeiro", "Resumo financeiro do dia anterior",
                mensagem, f"resumo:{est.id}:{inicio.date()}:usuario:{uid}",
                estacionamento_id=est.id, destino="/dashboard",
            ):
                count += 1
    return count
