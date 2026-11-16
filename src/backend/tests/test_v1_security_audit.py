"""PR65 — audit of denied privileges and incident response without altering roles."""
from models.db_models import EventoSeguranca


def test_denied_admin_access_is_logged_without_token_or_secret(client, db, fab):
    motorista = fab.usuario()
    admin = fab.usuario(role="admin")
    token = fab.token(motorista)
    denied = client.get("/api/admin/usuarios", headers=token)
    assert denied.status_code == 403, denied.text
    events = client.get("/api/admin/seguranca/eventos", headers=fab.token(admin))
    assert events.status_code == 200, events.text
    matches = [e for e in events.json() if e["usuario_id"] == motorista.id]
    assert any(e["categoria"] == "acesso_negado" and
               e["status_http"] == 403 for e in matches)
    assert all("Bearer" not in e["operacao"] and "?" not in e["operacao"]
               for e in events.json())
    assert client.get("/api/admin/seguranca/eventos", headers=token).status_code == 403


def test_manager_cannot_read_unrelated_denied_access(client, db, fab):
    est1 = fab.est("Shopping 1")
    est2 = fab.est("Shopping 2")
    gestor1 = fab.usuario(role="gestor", est=est1)
    gestor2 = fab.usuario(role="gestor", est=est2)
    # Gestor 1 accesses a global administrative endpoint and gets a 403.
    result = client.get("/api/admin/usuarios", headers=fab.token(gestor1))
    assert result.status_code == 403
    own = client.get("/api/admin/seguranca/eventos", headers=fab.token(gestor1))
    other = client.get("/api/admin/seguranca/eventos", headers=fab.token(gestor2))
    assert own.status_code == other.status_code == 200
    assert any(x["usuario_id"] == gestor1.id for x in own.json())
    assert all(x["usuario_id"] != gestor1.id for x in other.json())


def test_admin_can_revoke_compromised_user_sessions_and_audit(client, db, fab):
    usuario = fab.usuario(senha="senha-incidente123")
    admin = fab.usuario(role="admin")
    login = client.post("/auth/login", json={
        "email": usuario.email, "senha": "senha-incidente123",
    })
    assert login.status_code == 200, login.text
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/auth/me", headers=h).status_code == 200
    r = client.post(
        f"/api/admin/seguranca/usuarios/{usuario.id}/revogar-sessoes",
        headers=fab.token(admin),
    )
    assert r.status_code == 200, r.text
    assert r.json()["sessoes_revogadas"] >= 1
    assert client.get("/auth/me", headers=h).status_code == 401
    db.refresh(usuario)
    assert usuario.role == "usuario"
    assert usuario.is_ativo is True
    stored = db.query(EventoSeguranca).filter(
        EventoSeguranca.usuario_id == admin.id,
        EventoSeguranca.categoria == "resposta_incidente",
    ).count()
    assert stored >= 1
    assert client.post(
        f"/api/admin/seguranca/usuarios/{usuario.id}/revogar-sessoes",
        headers=h,
    ).status_code == 401
