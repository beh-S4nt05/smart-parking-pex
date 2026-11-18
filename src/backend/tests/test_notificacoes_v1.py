"""Regressão V1 — notificações idempotentes, usuários e filtros no backend real."""
from datetime import timedelta

from core.timeutils import utc_agora
from models.db_models import (
    AcompanhamentoVaga, EventoOperacional, Notificacao, TipoUsuario,
)
from models.schemas import ReservaCreate
from rules import notificacoes_service as notify, reserva_service


def _reserva(db, vaga, usuario, minutos=90):
    agora = utc_agora()
    return reserva_service.criar_reserva(
        db,
        ReservaCreate(
            vaga_id=vaga.id,
            horario_inicio=agora + timedelta(minutes=1),
            horario_fim=agora + timedelta(minutes=minutos),
        ),
        usuario,
    )


def test_reserva_cancelamento_gera_apenas_notificacoes_da_conta(db, fab, client):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    motorista = fab.usuario()
    outro = fab.usuario()
    reserva = _reserva(db, vaga, motorista)
    reserva_service.cancelar_reserva(db, reserva.id, motorista)

    minhas = db.query(Notificacao).filter(
        Notificacao.usuario_id == motorista.id,
        Notificacao.referencia_id == reserva.id,
    ).all()
    assert {n.tipo for n in minhas} == {"reserva_confirmada", "reserva_cancelada"}
    assert len(minhas) == 2
    assert all(n.usuario_id != outro.id for n in minhas)

    headers = fab.token(motorista)
    response = client.get("/api/notificacoes", headers=headers)
    assert response.status_code == 200
    assert {n["tipo"] for n in response.json() if n["referencia_id"] == reserva.id} == {
        "reserva_confirmada", "reserva_cancelada"
    }

    for n in minhas:
        assert client.patch(f"/api/notificacoes/{n.id}/ler", headers=fab.token(outro)).status_code == 404
        assert client.patch(f"/api/notificacoes/{n.id}/ler", headers=headers).status_code == 200
    count = client.get("/api/notificacoes/contador", headers=headers)
    assert count.status_code == 200
    assert count.json()["nao_lidas"] >= 0

    assert client.get("/api/notificacoes").status_code == 401
    assert client.patch("/api/notificacoes/ler-todas", headers=fab.token(outro)).status_code == 200


def test_lembrete_antes_prazo_idempotente_e_cancelado(db, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    usuario = fab.usuario()
    reserva = _reserva(db, vaga, usuario, minutos=14)
    n = notify.lembretes_pendentes(db)
    assert n == 1
    db.commit()
    assert notify.lembretes_pendentes(db) == 0
    db.commit()

    lembretes = db.query(Notificacao).filter(
        Notificacao.usuario_id == usuario.id,
        Notificacao.referencia_id == reserva.id,
        Notificacao.tipo == "lembrete_reserva",
    ).all()
    assert len(lembretes) == 1
    reserva_service.cancelar_reserva(db, reserva.id, usuario)
    assert notify.lembretes_pendentes(db) == 0


def test_central_preferencias_e_acompanhamento_escopo(db, fab, client):
    est, outro_est = fab.est(), fab.est()
    andar = fab.andar(est)
    user = fab.usuario()
    token = fab.token(user)
    p = client.get("/api/notificacoes/preferencias", headers=token)
    assert p.status_code == 200
    assert p.json()["push_ativo"] is False
    updated = {**p.json(), "vagas": True}
    assert client.put("/api/notificacoes/preferencias", json=updated, headers=token).status_code == 200
    assert client.get("/api/notificacoes/preferencias", headers=token).json()["vagas"] is True

    invalid = client.post("/api/notificacoes/acompanhamentos", headers=token, json={
        "estacionamento_id": outro_est.id, "andar_id": andar.id, "tipo_vaga": "comum"
    })
    assert invalid.status_code == 422

    dados = {"estacionamento_id": est.id, "andar_id": andar.id, "tipo_vaga": "comum"}
    a = client.post("/api/notificacoes/acompanhamentos", headers=token, json=dados)
    assert a.status_code == 201, a.text
    repeat = client.post("/api/notificacoes/acompanhamentos", headers=token, json=dados)
    assert repeat.status_code == 201
    assert repeat.json()["id"] == a.json()["id"]

    outro = fab.usuario()
    assert client.delete("/api/notificacoes/acompanhamentos/" + a.json()["id"], headers=fab.token(outro)).status_code == 404
    assert client.delete("/api/notificacoes/acompanhamentos/" + a.json()["id"], headers=token).status_code == 204


def test_disponibilidade_condicionada_a_evento_e_cooldown(db, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    motorista = fab.usuario()
    pref = notify.preferencias(db, motorista.id)
    pref.vagas = True
    acompanhamento = AcompanhamentoVaga(
        usuario_id=motorista.id, estacionamento_id=est.id,
        tipo_vaga="comum", ativo=True,
    )
    db.add(acompanhamento)
    ev = EventoOperacional(
        estacionamento_id=est.id, evento="vaga_liberada",
        vaga_id=vaga.id, origem="simulador",
        criado_em=utc_agora() - timedelta(seconds=15),
    )
    db.add(ev)
    db.commit()
    assert notify.disponibilidade_pendente(db) == 1
    db.commit()
    assert notify.disponibilidade_pendente(db) == 0
    count = db.query(Notificacao).filter_by(
        usuario_id=motorista.id, tipo="vaga_disponivel"
    ).count()
    assert count >= 1


def test_financeiro_sem_vazamento_para_gestor_ou_outro_shopping(db, fab):
    est, outro_est = fab.est(), fab.est()
    fin = fab.usuario(role=TipoUsuario.FINANCEIRO, est=est)
    outro_fin = fab.usuario(role=TipoUsuario.FINANCEIRO, est=outro_est)
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=est)
    admin = fab.usuario(role=TipoUsuario.ADMIN)
    recebedores = notify.financeiro_destinatarios(db, est.id)
    assert fin.id in recebedores
    assert admin.id in recebedores
    assert outro_fin.id not in recebedores
    assert gestor.id not in recebedores


def test_push_token_privado_e_logout_desvincula_dispositivo(db, fab, client, monkeypatch):
    from cryptography.fernet import Fernet
    from core.config import settings
    from models.db_models import DispositivoNotificacao

    usuario = fab.usuario()
    headers = fab.token(usuario)
    token_expo = "ExpoPushToken[TESTTOKEN123456789012]"
    response = client.post(
        "/api/notificacoes/dispositivos",
        headers=headers, json={"token": token_expo, "plataforma": "android"},
    )
    assert response.status_code == 503  # sem segredo privado não ativar push

    monkeypatch.setattr(settings, "NOTIFICATIONS_ENCRYPTION_KEY", Fernet.generate_key().decode())
    criado = client.post(
        "/api/notificacoes/dispositivos",
        headers=headers, json={"token": token_expo, "plataforma": "android"},
    )
    assert criado.status_code == 201, criado.text
    device_id = criado.json()["id"]
    device = db.get(DispositivoNotificacao, device_id)
    assert device.ativo is True
    assert token_expo not in device.token_expo

    logout = client.post(
        "/auth/logout", headers=headers,
        params={"notification_device_id": device_id},
    )
    assert logout.status_code == 204, logout.text
    db.refresh(device)
    assert device.ativo is False
