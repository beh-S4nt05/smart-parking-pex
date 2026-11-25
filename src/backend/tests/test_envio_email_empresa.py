"""Templates e transporte SMTP corporativo sem rede real em teste."""
import pytest
from fastapi import HTTPException

from core.config import settings
from core.email_templates import montar_email_transacional
from rules import identity_service


def test_email_tem_texto_html_legivel_e_codigo_em_destaque():
    mensagem = montar_email_transacional(
        "Smart Parking <naoresponda@empresa.exemplo>",
        "motorista@teste.dev",
        "Smart Parking - confirme seu e-mail",
        "Seu código de confirmação Smart Parking é: 012345\nValidade: 10 minutos.",
    )
    assert mensagem["To"] == "motorista@teste.dev"
    assert mensagem["From"].addresses[0].addr_spec == "naoresponda@empresa.exemplo"
    assert "012345" in mensagem.get_body(preferencelist=("plain",)).get_content()
    html = mensagem.get_body(preferencelist=("html",)).get_content()
    assert 'lang="pt-BR"' in html
    assert "012345" in html
    assert "SMART PARKING" in html


def test_template_escapa_html_inesperado():
    msg = montar_email_transacional(
        "empresa@teste.dev", "conta@teste.dev", "<script>alert(1)</script>",
        "Olá <img src=x onerror=alert(1)>",
    )
    html = msg.get_body(preferencelist=("html",)).get_content()
    assert "&lt;script&gt;" in html and "&lt;img" in html
    assert "<script>" not in html and "<img src=x" not in html


def test_smtp_rejeita_credencial_incompleta_antes_da_rede(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "SMTP_SENDER", "empresa@teste.dev")
    monkeypatch.setattr(settings, "SMTP_USER", "conta")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)
    monkeypatch.setattr(settings, "SMTP_SSL", False)
    monkeypatch.setattr(settings, "SMTP_STARTTLS", True)
    with pytest.raises(HTTPException) as exc:
        identity_service._enviar_email("alguem@teste.dev", "Assunto", "Corpo")
    assert exc.value.status_code == 503


def test_smtp_starttls_envia_mime_corporativo_sem_rede(monkeypatch):
    enviados = []
    class SMTPFalso:
        def __init__(self, host, porta, timeout=None):
            assert host == "smtp.test.local" and porta == 587 and timeout is not None
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def starttls(self, context=None):
            assert context is not None
        def login(self, usuario, senha):
            assert (usuario, senha) == ("conta", "credencial-smtp")
        def send_message(self, msg):
            enviados.append(msg)

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "SMTP_SENDER", "Smart Parking <empresa@teste.dev>")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USER", "conta")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "credencial-smtp")
    monkeypatch.setattr(settings, "SMTP_SSL", False)
    monkeypatch.setattr(settings, "SMTP_STARTTLS", True)
    monkeypatch.setattr(identity_service.smtplib, "SMTP", SMTPFalso)
    identity_service._enviar_email("alguem@teste.dev", "Smart Parking - código", "Código: 000001")
    assert len(enviados) == 1
    assert enviados[0]["To"] == "alguem@teste.dev"
    assert "Código: 000001" in enviados[0].get_body(preferencelist=("plain",)).get_content()
    assert enviados[0].get_body(preferencelist=("html",)) is not None
