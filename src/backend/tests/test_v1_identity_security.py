"""PR60: testes sem SMTP externo e sem expor tokens no log."""
import time

from core.identity_security import _hotp, hash_token, gerar_token_uso_unico, validar_totp
from core.config import settings


def test_totp_known_vector_and_replay():
    segredo = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert validar_totp(segredo, "287082", agora=59, tolerancia=0) == 1
    assert validar_totp(segredo, "287082", agora=59, ultimo_contador=1) is None
    assert validar_totp(segredo, "000000", agora=59, tolerancia=0) is None
    assert _hotp(segredo, 1) == "287082"


def test_one_use_tokens_are_random_and_not_stored_in_plaintext():
    token1, digest1 = gerar_token_uso_unico()
    token2, digest2 = gerar_token_uso_unico()
    assert token1 != token2 and digest1 != digest2
    assert digest1 != token1 and digest1 == hash_token(token1)


def test_email_confirmation_and_password_reset_require_valid_one_use_token(client, db, fab, monkeypatch):
    from rules import identity_service
    user = fab.usuario()
    enviados = []
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "SMTP_SENDER", "no-reply@test.local")
    monkeypatch.setattr(identity_service, "_enviar_email", lambda dest, titulo, corpo: enviados.append((dest, titulo, corpo)))
    req = client.post("/auth/email/solicitar", json={"email": user.email})
    assert req.status_code == 202, req.text
    token = enviados[-1][2].split(": ")[1].split("\n")[0]
    ok = client.post("/auth/email/confirmar", json={"token": token})
    assert ok.status_code == 204, ok.text
    db.refresh(user)
    assert user.email_verificado_em is not None
    assert client.post("/auth/email/confirmar", json={"token": token}).status_code == 400

    assert client.post("/auth/senha/esqueci", json={"email": user.email}).status_code == 202
    codigo = enviados[-1][2].split(": ")[1].split("\n")[0]
    reset = client.post("/auth/senha/redefinir", json={"token": codigo, "nova_senha": "senha-atualizada123"})
    assert reset.status_code == 204, reset.text
    assert client.post("/auth/senha/redefinir", json={"token": codigo, "nova_senha": "outro123"}).status_code == 400
    assert client.post("/auth/login", json={"email": user.email, "senha": "senha-atualizada123"}).status_code == 200


def test_staff_mfa_requires_otp_if_enabled_and_never_trusts_client_role(client, db, fab, monkeypatch):
    from cryptography.fernet import Fernet
    from models.db_models import TipoUsuario
    from rules.identity_service import _fernet
    staff = fab.usuario(role=TipoUsuario.GESTOR, senha="senha-gestor123")
    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    inicio = client.post("/auth/mfa/iniciar", json={"senha_atual": "senha-gestor123"}, headers=fab.token(staff))
    assert inicio.status_code == 200, inicio.text
    uri = inicio.json()["uri_totp"]
    assert uri.startswith("otpauth://totp/")
    db.refresh(staff)
    segredo = _fernet().decrypt(staff.mfa_segredo_cifrado.encode("ascii")).decode("ascii")
    code = _hotp(segredo, int(time.time()) // 30)
    assert client.post("/auth/mfa/confirmar", json={"codigo": code}, headers=fab.token(staff)).status_code == 204
    denied = client.post("/auth/login", json={"email": staff.email, "senha": "senha-gestor123"})
    assert denied.status_code == 401, denied.text
    denied_replay = client.post("/auth/login", json={"email": staff.email, "senha": "senha-gestor123", "mfa_codigo": code})
    assert denied_replay.status_code == 401
