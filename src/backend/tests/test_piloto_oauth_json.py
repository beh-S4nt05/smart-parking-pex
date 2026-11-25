"""Testes locais: formatos reais do client_secret Google e callback seguro."""
import json
import pytest

from piloto_autorizar_gmail import (
    _ler_cliente_oauth, _redirect_web, _validar_callback_local,
    _iniciar_servidor_callback,
)


def _json(tmp_path, conteudo):
    arquivo = tmp_path / "qualquer_nome_que_o_google_gerou.json"
    arquivo.write_text(json.dumps(conteudo), encoding="utf-8")
    return arquivo


def test_nome_arquivo_irrelevante_e_cliente_desktop(tmp_path):
    arquivo = _json(tmp_path, {
        "installed": {
            "client_id": "oauth-id.apps.googleusercontent.com",
            "client_secret": "segredo-privado",
            "redirect_uris": ["http://localhost"],
        }
    })
    tipo, client_id, segredo, uris = _ler_cliente_oauth(arquivo)
    assert tipo == "desktop"
    assert client_id.endswith(".apps.googleusercontent.com")
    assert segredo == "segredo-privado"
    assert uris == ["http://localhost"]


def test_cliente_web_e_callback_autorizado(tmp_path):
    uri = "http://localhost:8765/oauth/callback"
    arquivo = _json(tmp_path, {
        "web": {
            "client_id": "id",
            "client_secret": "senha",
            "redirect_uris": ["https://exemplo.com/oauth", uri],
        }
    })
    tipo, _, _, uris = _ler_cliente_oauth(arquivo)
    assert tipo == "web"
    assert _redirect_web(uris, None) == uri
    assert _validar_callback_local(uri) == ("localhost", 8765, "/oauth/callback")


def test_formato_plano_recebido_de_outros_exportadores(tmp_path):
    arquivo = _json(tmp_path, {"client_id": "id", "client_secret": "senha"})
    assert _ler_cliente_oauth(arquivo)[0] == "web"
    assert _redirect_web([], "http://127.0.0.1:8765/oauth/callback").endswith("/oauth/callback")


def test_cliente_web_sem_uri_local_exibe_correcao_exata(tmp_path):
    arquivo = _json(tmp_path, {
        "web": {"client_id": "id", "client_secret": "senha",
                "redirect_uris": ["https://app.exemplo.com/retorno"]}
    })
    _, _, _, uris = _ler_cliente_oauth(arquivo)
    with pytest.raises(ValueError, match=r"--redirect-uri http://127\\.0\\.0\\.1:8765/oauth/callback"):
        _redirect_web(uris, None)


@pytest.mark.parametrize("uri", [
    "https://app.exemplo.com/callback",
    "http://localhost/oauth/callback",
    "http://0.0.0.0:8765/oauth/callback",
    "http://evil.com:8765/oauth/callback",
    "http://localhost:8765/oauth/callback?token=1",
    "http://localhost:8765/oauth/callback#fragment",
    "http://user:password@localhost:8765/oauth/callback",
])
def test_callback_nao_pode_sair_da_maquina_local(uri):
    with pytest.raises(ValueError):
        _validar_callback_local(uri)


def test_erro_para_json_nao_oauth_sem_vazar_conteudo(tmp_path):
    arquivo = _json(tmp_path, {"type": "service_account", "private_key": "MUITO_PRIVADO"})
    with pytest.raises(ValueError, match="conta de serviço") as exc:
        _ler_cliente_oauth(arquivo)
    assert "MUITO_PRIVADO" not in str(exc.value)


def test_listener_local_aceita_porta_dinamica_ou_fixa():
    servidor, estado = _iniciar_servidor_callback(porta=0, rota="/outro/callback")
    try:
        assert servidor.server_address[0] == "127.0.0.1"
        assert servidor.server_address[1] > 0
        assert estado == {}
    finally:
        servidor.server_close()
