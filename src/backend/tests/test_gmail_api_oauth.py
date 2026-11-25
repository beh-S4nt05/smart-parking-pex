"""Gmail API OAuth 2.0: transporte server-side, cache e teste sem rede real."""
import base64
import os
import stat

import httpx
import pytest
from fastapi import HTTPException

from core import gmail_api
from core.config import settings
from rules import identity_service
from piloto_autorizar_gmail import _salvar_env_privado


class ClienteGmailFalso:
    chamadas = []

    def __init__(self, timeout):
        assert timeout == 12.0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, url, **kwargs):
        self.chamadas.append((url, kwargs))
        if url.endswith("/token"):
            assert kwargs["data"]["grant_type"] == "refresh_token"
            assert kwargs["data"]["refresh_token"] == "refresh-privado"
            return httpx.Response(
                200, json={"access_token": "access-curto", "expires_in": 3600},
                request=httpx.Request("POST", url),
            )
        assert url == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        assert kwargs["headers"]["Authorization"] == "Bearer access-curto"
        return httpx.Response(
            200, json={"id": "id-mensagem-enviada"},
            request=httpx.Request("POST", url),
        )


def _gmail_configurado(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "gmail_api")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "client-secret-privado")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-privado")
    monkeypatch.setattr(settings, "GMAIL_SENDER", "Smart Parking <conta@empresa.teste>")
    monkeypatch.setattr(gmail_api, "_access_token", None)
    monkeypatch.setattr(gmail_api, "_access_token_expira_monotonic", 0.0)


def test_envio_gmail_api_sem_senha_smtp_e_com_token_cache(monkeypatch):
    _gmail_configurado(monkeypatch)
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(settings, "SMTP_SENDER", None)
    ClienteGmailFalso.chamadas = []
    monkeypatch.setattr(gmail_api.httpx, "Client", ClienteGmailFalso)

    assert identity_service._transporte_disponivel() is True
    identity_service._enviar_email(
        "motorista@teste.dev", "Smart Parking - confirme seu e-mail",
        "Seu código de confirmação Smart Parking é: 012345\nValidade: 10 minutos.",
    )
    identity_service._enviar_email("outra@teste.dev", "Smart Parking", "Teste")
    assert [url for url, _ in ClienteGmailFalso.chamadas].count(
        "https://oauth2.googleapis.com/token"
    ) == 1
    assert len(ClienteGmailFalso.chamadas) == 3
    _, envio = ClienteGmailFalso.chamadas[1]
    raw = envio["json"]["raw"]
    original = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    assert b"motorista@teste.dev" in original
    assert b"012345" in original
    assert b"refresh-privado" not in original
    assert b"client-secret-privado" not in original


def test_gmail_api_falha_503_sem_vazar_segredos(monkeypatch):
    _gmail_configurado(monkeypatch)
    def responder(request):
        return httpx.Response(401, json={"error": "invalid_grant", "detail": "secret"})
    monkeypatch.setattr(gmail_api.httpx, "Client",
                        lambda timeout: httpx.Client(transport=httpx.MockTransport(responder), timeout=timeout))
    # Usar cliente HTTP original no fake de transporte; substituir só o transporte sem recursão.
    cliente_real = httpx.Client
    monkeypatch.setattr(gmail_api.httpx, "Client",
                        lambda timeout: cliente_real(transport=httpx.MockTransport(responder), timeout=timeout))
    with pytest.raises(HTTPException) as exc:
        gmail_api.enviar_email_gmail("motorista@teste.dev", "Teste", "Mensagem")
    assert exc.value.status_code == 503
    assert "secret" not in exc.value.detail
    assert "refresh-privado" not in exc.value.detail


def test_arquivo_oauth_privado_preserva_configuracoes(tmp_path):
    env = tmp_path / ".env.piloto"
    env.write_text("SECRET_KEY=segredo-existente\nEMAIL_PROVIDER=smtp\n", encoding="utf-8")
    _salvar_env_privado(env, {
        "EMAIL_PROVIDER": "gmail_api",
        "GMAIL_REFRESH_TOKEN": "token-ficticio",
    })
    dado = env.read_text(encoding="utf-8")
    assert "SECRET_KEY=segredo-existente" in dado
    assert 'EMAIL_PROVIDER="gmail_api"' in dado
    assert 'GMAIL_REFRESH_TOKEN="token-ficticio"' in dado
    assert stat.S_IMODE(os.stat(env).st_mode) == 0o600
