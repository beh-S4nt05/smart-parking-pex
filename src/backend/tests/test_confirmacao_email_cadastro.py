"""Confirmação SMTP real: cadastro pendente, envio, OTP e proteção anti-bruteforce."""
import uuid

from core.config import settings
from models.db_models import Usuario
from rules import identity_service


def _novo_email():
    return f"otp-{uuid.uuid4().hex}@teste.dev"


def _dados(email):
    return {"nome": "Motorista Cadastro", "email": email, "senha": "SenhaForte2026!"}


def _mockar_empresa(monkeypatch):
    enviados = []
    monkeypatch.setattr(settings, "SECURITY_VERIFIED_EMAIL_REQUIRED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.empresa.teste")
    monkeypatch.setattr(settings, "SMTP_SENDER", "Smart Parking <naoresponda@empresa.teste>")
    monkeypatch.setattr(identity_service, "_enviar_email", lambda para, assunto, corpo: enviados.append((para, assunto, corpo)))
    return enviados


def test_novo_cadastro_recebe_codigo_e_so_ativa_login_depois_da_confirmacao(client, db, monkeypatch):
    enviados = _mockar_empresa(monkeypatch)
    email = _novo_email()
    registro = client.post("/auth/registrar", json=_dados(email))
    assert registro.status_code == 201, registro.text
    assert registro.json()["confirmacao_email_pendente"] is True
    assert registro.json()["email_enviado"] is True
    assert len(enviados) == 1 and enviados[0][0] == email
    codigo = enviados[0][2].split(": ")[1].split("\n")[0]
    assert len(codigo) == 6 and codigo.isdecimal()
    assert codigo not in str(db.query(Usuario).filter(Usuario.email == email).one().__dict__)

    login = client.post("/auth/login", json={"email": email, "senha": "SenhaForte2026!"})
    assert login.status_code == 403 and "Confirme" in login.text

    confirmado = client.post("/auth/email/confirmar", json={"email": email, "codigo": codigo})
    assert confirmado.status_code == 204, confirmado.text
    login2 = client.post("/auth/login", json={"email": email, "senha": "SenhaForte2026!"})
    assert login2.status_code == 200, login2.text
    assert client.post("/auth/email/confirmar", json={"email": email, "codigo": codigo}).status_code == 409


def test_codigo_invalido_so_permita_cinco_tentativas(client, monkeypatch):
    enviados = _mockar_empresa(monkeypatch)
    email = _novo_email()
    assert client.post("/auth/registrar", json=_dados(email)).status_code == 201
    valido = enviados[0][2].split(": ")[1].split("\n")[0]
    invalido = "000000" if valido != "000000" else "999999"
    for _ in range(5):
        erro = client.post("/auth/email/confirmar", json={"email": email, "codigo": invalido})
        assert erro.status_code == 400, erro.text
    assert client.post("/auth/email/confirmar", json={"email": email, "codigo": valido}).status_code == 400


def test_sem_smtp_cadastro_obrigatorio_nao_cria_conta(client, db, monkeypatch):
    monkeypatch.setattr(settings, "SECURITY_VERIFIED_EMAIL_REQUIRED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(settings, "SMTP_SENDER", None)
    email = _novo_email()
    retorno = client.post("/auth/registrar", json=_dados(email))
    assert retorno.status_code == 503
    assert db.query(Usuario).filter(Usuario.email == email).count() == 0
