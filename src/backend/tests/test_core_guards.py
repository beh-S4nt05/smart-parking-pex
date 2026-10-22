"""M2-02/M2-03 — guardas de config em produção e chave do rate limiter."""

import types

import pytest
from pydantic import ValidationError

from core.config import Settings
from core.rate_limiter import get_user_or_ip

DEFAULT_SK = "sua_chave_secreta_de_producao_aqui"
DEFAULT_SIGN = "smartparking_default_signing_key_change_in_production"


def test_producao_recusa_chaves_de_exemplo():
    with pytest.raises(ValidationError) as exc:
        Settings(ENVIRONMENT="production", SECRET_KEY=DEFAULT_SK)
    assert "SECRET_KEY" in str(exc.value)

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="k" * 40,
            APP_SIGNING_SECRET=DEFAULT_SIGN,
        )

    ok = Settings(
        ENVIRONMENT="production", SECRET_KEY="k" * 40, APP_SIGNING_SECRET="s" * 40
    )
    assert ok.ENVIRONMENT == "production"


def test_desenvolvimento_livre_das_garras():
    s = Settings(ENVIRONMENT="development")
    assert s.SECRET_KEY  # qualquer uma vale fora de produção


def _req(auth=None):
    return types.SimpleNamespace(
        headers={"Authorization": auth} if auth else {},
        client=types.SimpleNamespace(host="10.1.2.3"),
    )


def test_rate_limit_key_identifica_usuarios_diferentes():
    # ACH-04: os 32 primeiros chars de um JWT são o HEADER — idênticos para
    # todos. A chave nova precisa separar dois usuários com tokens que só
    # diferem no payload.
    head = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    k1 = get_user_or_ip(_req("Bearer " + head + "AAAA"))
    k2 = get_user_or_ip(_req("Bearer " + head + "BBBB"))
    assert k1 != k2 and k1.startswith("user:")

    k3 = get_user_or_ip(_req())
    assert k3.startswith("ip:")


def test_rotas_sociais_404_com_flag_desligada(client):
    """ACH-08/M2-04: sem LOGIN_SOCIAL_ENABLED as rotas OAuth respondem 404."""
    r = client.post("/auth/login/google", json={"id_token": "qualquer"})
    assert r.status_code == 404
    assert "desabilitado" in r.json()["detail"]
