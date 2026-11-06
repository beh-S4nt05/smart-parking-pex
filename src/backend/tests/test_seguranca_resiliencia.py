"""Segurança de entrada e continuidade diante de dados hostis ou sobredimensionados."""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.config import Settings
from core.security import criar_hash_senha, verificar_senha
from core.security_middleware import SecurityHeadersMiddleware


def _config_producao(**kwargs):
    config = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "k" * 40,
        "APP_SIGNING_SECRET": "s" * 40,
        **kwargs,
    }
    return Settings(**config)


def test_login_com_senha_enorme_nao_gera_500_e_api_continua_saudavel(client, fab):
    usuario = fab.usuario(senha="senha123")
    resposta = client.post(
        "/auth/login", json={"email": usuario.email, "senha": "x" * 4096}
    )
    assert resposta.status_code == 401, resposta.text
    assert "traceback" not in resposta.text.lower()
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("senha", ["a" * 73, "á" * 72])
def test_cadastro_recusa_senha_acima_do_limite_real_do_bcrypt(client, db, senha):
    from models.db_models import Usuario

    email = f"senha-longa-{uuid.uuid4().hex[:8]}@teste.dev"
    resposta = client.post(
        "/auth/registrar",
        json={"nome": "QA senha longa", "email": email, "senha": senha},
    )
    assert resposta.status_code == 422, resposta.text
    assert db.query(Usuario).filter(Usuario.email == email).first() is None
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("senha", ["a" * 72, "á" * 36])
def test_bcrypt_aceita_exatamente_72_bytes_sem_truncar(senha):
    senha_hash = criar_hash_senha(senha)
    assert verificar_senha(senha, senha_hash) is True
    assert verificar_senha(senha + "x", senha_hash) is False


def test_hash_bcrypt_invalido_falha_fechado():
    assert verificar_senha("senha123", "hash-corrompido") is False


def test_json_malformado_retorna_4xx_e_nao_derruba_aplicacao(client):
    resposta = client.post(
        "/auth/login",
        content=b'{"email":"quebrado"',
        headers={"Content-Type": "application/json"},
    )
    assert 400 <= resposta.status_code < 500, resposta.text
    assert "traceback" not in resposta.text.lower()
    assert client.get("/health").status_code == 200


def test_corpo_acima_de_1mib_recebe_413_e_api_segue_respondendo(client):
    corpo = b'{"email":"' + (b"a" * (1024 * 1024 + 100)) + b'","senha":"x"}'
    resposta = client.post(
        "/auth/login", content=corpo, headers={"Content-Type": "application/json"}
    )
    assert resposta.status_code == 413, resposta.text
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/health").status_code == 200


def test_corpo_chunked_tambem_respeita_o_limite(client):
    def partes():
        yield b'{"email":"'
        yield b"a" * (1024 * 1024 + 100)
        yield b'","senha":"x"}'

    resposta = client.post(
        "/auth/login", content=partes(), headers={"Content-Type": "application/json"}
    )
    assert resposta.status_code == 413, resposta.text
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("campo", ["SECRET_KEY", "APP_SIGNING_SECRET"])
def test_producao_recusa_chaves_mesmo_nao_padrao_com_menos_de_32_bytes(campo):
    kwargs = {campo: "curta"}
    with pytest.raises(ValidationError, match="32 bytes"):
        _config_producao(**kwargs)


def test_producao_recusa_regex_cors_abrangente_e_desliga_debug():
    with pytest.raises(ValidationError, match="CORS"):
        _config_producao(CORS_ORIGIN_REGEX="^https?://.*$")

    config = _config_producao(DEBUG=True)
    assert config.DEBUG is False


def test_bloqueios_de_producao_também_tem_headers_de_seguranca():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, environment="production")

    @app.get("/")
    def raiz():
        return {"ok": True}

    with TestClient(app) as cliente:
        respostas = [
            cliente.get("/", headers={"User-Agent": "sqlmap/1.8"}),
            cliente.request("TRACE", "/"),
        ]
        for resposta in respostas:
            assert resposta.status_code in {403, 405}
            assert resposta.headers["X-Content-Type-Options"] == "nosniff"
            assert resposta.headers["X-Frame-Options"] == "DENY"
            assert "frame-ancestors 'none'" in resposta.headers["Content-Security-Policy"]
            assert "server" not in resposta.headers
