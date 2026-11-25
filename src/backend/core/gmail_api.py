"""Transporte Gmail API (OAuth 2.0 offline) para e-mails transacionais.

A autorização pertence à conta da empresa; nenhuma credencial Google é
repassada a clientes Web/Android/iOS nem exposta por rotas públicas.
"""
import base64
import threading
import time

import httpx
from fastapi import HTTPException

from core.config import settings
from core.email_templates import montar_email_transacional

_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_SEND_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

_lock = threading.Lock()
_access_token: str | None = None
_access_token_expira_monotonic = 0.0


def gmail_api_configurada() -> bool:
    """Somente verifica as variáveis presentes, sem emitir chamadas externas."""
    return bool(
        settings.GMAIL_CLIENT_ID
        and settings.GMAIL_CLIENT_SECRET
        and settings.GMAIL_REFRESH_TOKEN
        and settings.GMAIL_SENDER
    )


def _access_token_atual(cliente: httpx.Client) -> str:
    """Atualiza o access token no backend, com cache de segurança por worker."""
    global _access_token, _access_token_expira_monotonic
    with _lock:
        agora = time.monotonic()
        if _access_token and agora < _access_token_expira_monotonic:
            return _access_token
        try:
            resposta = cliente.post(
                _TOKEN_ENDPOINT,
                data={
                    "client_id": settings.GMAIL_CLIENT_ID,
                    "client_secret": settings.GMAIL_CLIENT_SECRET,
                    "refresh_token": settings.GMAIL_REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                },
            )
            resposta.raise_for_status()
            dados = resposta.json()
            token = dados.get("access_token")
            if not isinstance(token, str) or not token:
                raise ValueError("Resposta OAuth sem access_token")
            segundos = int(dados.get("expires_in", 3600))
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise HTTPException(
                status_code=503,
                detail="Falha na autorização do e-mail da empresa. Verifique OAuth 2.0 no servidor.",
            ) from None

        _access_token = token
        _access_token_expira_monotonic = agora + max(0, segundos - 120)
        return token


def enviar_email_gmail(destino: str, assunto: str, corpo: str) -> None:
    """Entrega via users.messages.send; sem senha SMTP ou Gmail API no APK."""
    if not gmail_api_configurada():
        raise HTTPException(status_code=503, detail="Gmail API não configurada no servidor")

    mensagem = montar_email_transacional(settings.GMAIL_SENDER, destino, assunto, corpo)
    raw = base64.urlsafe_b64encode(mensagem.as_bytes()).decode("ascii")
    try:
        with httpx.Client(timeout=12.0) as cliente:
            bearer = _access_token_atual(cliente)
            resposta = cliente.post(
                _SEND_ENDPOINT,
                headers={"Authorization": f"Bearer {bearer}"},
                json={"raw": raw},
            )
            resposta.raise_for_status()
            # Evita falso positivo ao receber resposta HTTP 200 malformada.
            dados = resposta.json()
            if not isinstance(dados, dict) or not dados.get("id"):
                raise ValueError("Resposta da Gmail API sem ID")
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(
            status_code=503,
            detail="Falha no envio pelo Gmail API. Verifique autorização, remetente e quotas.",
        ) from None
