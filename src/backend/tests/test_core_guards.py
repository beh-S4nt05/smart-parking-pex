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


def test_producao_recusa_cors_curinga():
    with pytest.raises(ValidationError, match="CORS curinga"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="k" * 40,
            APP_SIGNING_SECRET="s" * 40,
            CORS_ORIGINS=["*"],
        )


def test_cors_web_permite_somente_frontend_local_ou_lan():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    from core.cors import opcoes_cors

    app = FastAPI()
    app.add_middleware(CORSMiddleware, **opcoes_cors(Settings(ENVIRONMENT="development")))

    @app.post("/auth/login")
    def login():
        return {"ok": True}

    with TestClient(app) as cliente:
        for origem in (
            "http://localhost:8081",
            "http://127.0.0.1:8081",
            "http://192.168.1.14:8081",
            "http://10.0.2.2:8081",
            "http://169.254.0.21:8081",
            "http://servidor.local:8081",
            "http://172.18.0.2:8081",
        ):
            resposta = cliente.options(
                "/auth/login",
                headers={
                    "Origin": origem,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )
            assert resposta.status_code == 200
            assert resposta.headers["access-control-allow-origin"] == origem
            assert resposta.headers["access-control-allow-credentials"] == "true"

        for origem in (
            "https://evil.example",
            "http://192.168.1.14.evil.example:8081",
            "http://servidor.local.evil.example:8081",
            "http://192.168.1.14:9000",
        ):
            resposta = cliente.options(
                "/auth/login",
                headers={
                    "Origin": origem,
                    "Access-Control-Request-Method": "POST",
                },
            )
            assert resposta.status_code == 400
            assert "access-control-allow-origin" not in resposta.headers


def test_cors_production_nao_ganha_excecao_lan_implicita():
    from core.cors import opcoes_cors

    producao = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="k" * 40,
        APP_SIGNING_SECRET="s" * 40,
        CORS_ORIGINS=["https://parking.example.com"],
    )
    opcoes = opcoes_cors(producao)
    assert opcoes["allow_origins"] == ["https://parking.example.com"]
    assert opcoes["allow_origin_regex"] is None

    fechado = opcoes_cors(
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="k" * 40,
            APP_SIGNING_SECRET="s" * 40,
        )
    )
    assert fechado["allow_origins"] == []
    assert fechado["allow_origin_regex"] is None


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


@pytest.mark.parametrize(
    ("host", "esperado"),
    [
        ("localhost", 200),
        ("127.0.0.1:8000", 200),
        ("192.168.1.14:8000", 200),
        ("10.0.2.2", 200),
        ("172.18.0.2:8000", 200),
        ("192.168.1.14.evil.example", 400),
        ("evil.example", 400),
        ("192.168.1.14:porta-invalida", 400),
    ],
)
def test_trusted_host_production_aceita_lan_sem_derrubar_stack(host, esperado):
    """Os curingas de IP não podem virar 500 nem liberar um Host inválido."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.trusted_host import TrustedHostLANMiddleware

    app = FastAPI()
    app.add_middleware(
        TrustedHostLANMiddleware,
        allowed_hosts=[*Settings().TRUSTED_HOSTS, "*.example.com"],
    )

    @app.get("/")
    def raiz():
        return {"ok": True}

    with TestClient(app, raise_server_exceptions=False) as cliente:
        resposta = cliente.get("/", headers={"Host": host})
        assert resposta.status_code == esperado


def test_trusted_host_mantem_wildcard_de_dominio():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.trusted_host import TrustedHostLANMiddleware

    app = FastAPI()
    app.add_middleware(TrustedHostLANMiddleware, allowed_hosts=["*.example.com"])

    @app.get("/")
    def raiz():
        return {"ok": True}

    with TestClient(app) as cliente:
        assert cliente.get("/", headers={"Host": "api.example.com"}).status_code == 200
        assert cliente.get("/", headers={"Host": "example.net"}).status_code == 400
