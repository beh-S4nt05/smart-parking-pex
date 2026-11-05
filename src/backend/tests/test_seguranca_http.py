"""Contratos dos middlewares de segurança em modo de produção."""

import hashlib
import hmac
import json
import time
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.body_limit import RequestBodyLimitMiddleware
from core.config import settings
from core.request_validator import RequestValidationMiddleware
from core.security_middleware import SecurityHeadersMiddleware


def _app_assinado(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    app = FastAPI()
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, environment="production")
    app.add_middleware(RequestBodyLimitMiddleware)

    @app.post("/api/echo")
    def echo(dados: dict):
        return {"recebido": dados}

    return TestClient(app)


def _headers_assinatura(corpo: bytes, path="/api/echo", timestamp=None, nonce=None):
    timestamp = timestamp or str(int(time.time()))
    nonce = nonce or uuid.uuid4().hex
    canonico = "\n".join(["POST", path, timestamp, nonce, corpo.decode("utf-8")])
    assinatura = hmac.new(
        settings.APP_SIGNING_SECRET.encode("utf-8"), canonico.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Request-Timestamp": timestamp,
        "X-Request-Nonce": nonce,
        "X-Request-Signature": assinatura,
    }


def test_escrita_em_producao_exige_assinatura(monkeypatch):
    client = _app_assinado(monkeypatch)
    response = client.post("/api/echo", json={"teste": True})
    assert response.status_code == 403
    assert "Assinatura ausente" in response.json()["detail"]


def test_assinatura_valida_aceita_body_e_query_e_replay_e_rejeitado(monkeypatch):
    client = _app_assinado(monkeypatch)
    corpo = json.dumps({"teste": True}, separators=(",", ":")).encode()
    path = "/api/echo?origem=ui"
    headers = _headers_assinatura(corpo, path=path)

    valida = client.post(path, content=corpo, headers=headers)
    replay = client.post(path, content=corpo, headers=headers)

    assert valida.status_code == 200, valida.text
    assert valida.json() == {"recebido": {"teste": True}}
    assert replay.status_code == 403
    assert "duplicada" in replay.json()["detail"]


def test_assinatura_não_aceita_body_adulterado_ou_timestamp_expirado(monkeypatch):
    client = _app_assinado(monkeypatch)
    original = b'{"valor":1}'
    headers = _headers_assinatura(original)

    adulterado = client.post("/api/echo", content=b'{"valor":2}', headers=headers)
    expirado = client.post(
        "/api/echo",
        content=original,
        headers=_headers_assinatura(original, timestamp=str(int(time.time()) - 301)),
    )

    assert adulterado.status_code == 403
    assert "Assinatura inválida" in adulterado.json()["detail"]
    assert expirado.status_code == 403
    assert "expirada" in expirado.json()["detail"]


def test_headers_de_seguranca_e_remocao_de_fingerprint_em_producao():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, environment="production")

    @app.get("/")
    def raiz():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Strict-Transport-Security"].startswith("max-age=31536000")
    assert response.headers["Cache-Control"].startswith("no-store")
    assert "server" not in response.headers
    assert "x-powered-by" not in response.headers


def test_scanner_conhecido_e_metodo_de_enumeracao_são_bloqueados():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, environment="production")

    @app.get("/")
    def raiz():
        return {"ok": True}

    client = TestClient(app)
    scanner = client.get("/", headers={"User-Agent": "sqlmap/1.8"})
    metodo = client.request("TRACE", "/")

    assert scanner.status_code == 403
    assert metodo.status_code == 405
