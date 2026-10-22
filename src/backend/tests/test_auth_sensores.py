"""RF-13/14/15 (sessões) + RF-45 (sensores) + RF-32/33 (edições de painel)."""
<<<<<<< HEAD
=======
from datetime import UTC
>>>>>>> eb64687f68d74c589beca0aaf9d41bbce94aeffd


def _login_admin(db):
    from core.security import criar_token
    from models.db_models import Usuario

    admin = db.query(Usuario).filter(Usuario.email == "admin@smartparking.com").first()
    assert admin is not None
    return {"Authorization": f"Bearer {criar_token(admin.id, 'access')}"}


def _novo_usuario(client, senha="senha123"):
    import uuid

    sufixo = uuid.uuid4().hex[:8]
    email = f"rf13.{sufixo}@teste.dev"
    r = client.post("/auth/registrar", json={"nome": f"QA {sufixo}", "email": email, "senha": senha})
    assert r.status_code == 201, r.text
    login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert login.status_code == 200
    toks = login.json()
    toks["email"] = email
    return toks, {"Authorization": f"Bearer {toks['access_token']}"}


# ---------------- RF-13 · logout revoga no servidor ----------------

def test_logout_revoga_access_e_refresh(client, db, fab):
    toks, h = _novo_usuario(client)
    assert client.get("/auth/me", headers=h).status_code == 200
    r = client.post("/auth/logout", params={"refresh_token": toks["refresh_token"]}, headers=h)
    assert r.status_code == 204
    assert client.get("/auth/me", headers=h).status_code == 401  # access morto
    ren = client.post("/auth/refresh", json={"refresh_token": toks["refresh_token"]})
    assert ren.status_code == 401  # cadeia de renovação também


def test_tokens_legados_sem_jti_continuam_validos(client, db, fab):
    """Compat 22/10: token emitido antes do campo jti não é barrado."""
<<<<<<< HEAD
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone
=======
    from datetime import datetime, timedelta

    import jwt as pyjwt
>>>>>>> eb64687f68d74c589beca0aaf9d41bbce94aeffd

    from core.config import settings

    usuario = fab.usuario()
    db.commit()
<<<<<<< HEAD
    agora = datetime.now(timezone.utc)
=======
    agora = datetime.now(UTC)
>>>>>>> eb64687f68d74c589beca0aaf9d41bbce94aeffd
    leg = pyjwt.encode(
        {"sub": usuario.id, "type": "access", "iat": agora, "exp": agora + timedelta(minutes=5)},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {leg}"})
    assert r.status_code == 200


# ---------------- RF-15 · perfil ----------------

def test_editar_perfil_e_trocar_senha_com_relogin(client, db, fab):
    toks, h = _novo_usuario(client)
    r = client.put("/auth/me", json={"telefone": "92999990000", "placa_veiculo": "rra1a23"}, headers=h)
    assert r.status_code == 200, r.text
    me = client.get("/auth/me", headers=h).json()
    assert me["placa_veiculo"] == "RRA1A23"  # normalizada p/ maiúsculas

    bad = client.put("/auth/senha", json={"senha_atual": "nao-e", "nova_senha": "nova123"}, headers=h)
    assert bad.status_code == 401

    ok = client.put("/auth/senha", json={"senha_atual": "senha123", "nova_senha": "nova123"}, headers=h)
    assert ok.status_code == 204
    # padrão "mudei a senha, religue": token atual cai; nova senha entra
    assert client.get("/auth/me", headers=h).status_code == 401
    assert client.post("/auth/login", json={"email": toks["email"], "senha": "nova123"}).status_code == 200
    assert client.post("/auth/login", json={"email": toks["email"], "senha": "senha123"}).status_code == 401


# ---------------- RF-14 · reset de balcão pelo admin ----------------

def test_admin_reset_senha_derruba_sessoes(client, db, fab):
    toks, h = _novo_usuario(client)
    admin_h = _login_admin(db)
    r = client.post(f"/api/admin/usuarios/{toks['user']['id']}/reset-senha", headers=admin_h)
    assert r.status_code == 200, r.text
    temporaria = r.json()["senha_temporaria"]
    assert len(temporaria) == 10
    # sessão antiga do usuário morreu na hora
    assert client.get("/auth/me", headers=h).status_code == 401
    # e só a senha temporária entra
    assert client.post("/auth/login", json={"email": toks["email"], "senha": "senha123"}).status_code == 401
    assert client.post("/auth/login", json={"email": toks["email"], "senha": temporaria}).status_code == 200


# ---------------- RF-32/33 · edições ----------------

def test_put_andar_capacidade_e_vaga_tipo(client, db, fab):
    est = fab.est(); andar = fab.andar(est, capacidade=4)
    fab.vaga(andar); fab.vaga(andar)
    h = _login_admin(db)

    baixo = client.put(f"/api/admin/andares/{andar.id}", json={"capacidade": 1}, headers=h)
    assert baixo.status_code == 422  # menor que as 2 vagas reais do andar
    certo = client.put(f"/api/admin/andares/{andar.id}", json={"capacidade": 6, "numero_andar": 2}, headers=h)
    assert certo.status_code == 200
    assert certo.json()["capacidade"] == 6 and certo.json()["numero_andar"] == 2

    from models.db_models import Vaga

    vaga = db.query(Vaga).filter(Vaga.andar_id == andar.id).first()
    ed = client.put(f"/api/admin/vagas/{vaga.id}", json={"tipo": "pcd", "codigo": "qa-01"}, headers=h)
    assert ed.status_code == 200, ed.text
    assert ed.json()["tipo"] == "pcd" and ed.json()["codigo"] == "QA-01"
    # colisão de código no MESMO andar → 409
    outra = fab.vaga(andar)
    conf = client.put(f"/api/admin/vagas/{outra.id}", json={"codigo": "QA-01"}, headers=h)
    assert conf.status_code == 409


# ---------------- RF-45 · ingestão de sensores ----------------

def test_sensor_chave_idempotencia_e_aplicacao(client, db, fab):
    est = fab.est(); andar = fab.andar(est); vaga = fab.vaga(andar, codigo="A01")
    h = _login_admin(db)

    em = client.post("/api/admin/sensores", json={"estacionamento_id": est.id, "codigo": "sns-t1"}, headers=h)
    assert em.status_code == 201, em.text
    corpo = em.json()
    chave = corpo["chave"]
    assert corpo["codigo"] == "SNS-T1" and chave.startswith("SPK-")

    base = {"eventos": [{"seq": 1, "codigo_vaga": "A01", "status": "ocupada"}]}
    ok = client.post("/api/sensores/eventos", json=base, headers={"X-Device-Key": chave})
    assert ok.status_code == 200, ok.text
    assert ok.json()["aceitos"] == 1
    db.refresh(vaga)
    assert vaga.status == "ocupada"

    # reenvio do MESMO seq → duplicado (não gera segunda estadia)
    dup = client.post("/api/sensores/eventos", json=base, headers={"X-Device-Key": chave})
    assert dup.json()["duplicados"] == 1 and dup.json()["aceitos"] == 0

    # status inválido → ignorado com erro descritivo
    ruim = client.post(
        "/api/sensores/eventos",
        json={"eventos": [{"seq": 2, "codigo_vaga": "A01", "status": "queimada"}]},
        headers={"X-Device-Key": chave},
    )
    assert ruim.json()["ignorados"] == 1 and "queimada" in ruim.json()["erros"][0]

    # chave errada → 401; gestor NÃO emite (admin-only, família do simulador)
    assert client.post("/api/sensores/eventos", json=base, headers={"X-Device-Key": "SPK-lixo"}).status_code == 401
    gestor = fab.usuario(role="gestor", est=est)
    assert client.post("/api/admin/sensores", json={"estacionamento_id": est.id, "codigo": "X"}, headers=fab.token(gestor)).status_code == 403

    # revogar mata a chave antiga
    rev = client.post(f"/api/admin/sensores/{corpo['id']}/revogar", headers=h)
    assert rev.status_code == 200
    pos = client.post(
        "/api/sensores/eventos",
        json={"eventos": [{"seq": 9, "codigo_vaga": "A01", "status": "livre"}]},
        headers={"X-Device-Key": chave},
    )
    assert pos.status_code == 401
