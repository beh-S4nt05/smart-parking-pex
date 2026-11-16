"""Regressões do gerador de QR e da rota de sessões do simulador."""

import base64
import builtins
from io import BytesIO

from PIL import Image

from models.db_models import TipoUsuario
from rules import simulador_service


def _payload(estacionamento_id: str, andar_numero: int = 1) -> dict:
    return {
        "estacionamento_id": estacionamento_id,
        "andar_numero": andar_numero,
        "expira_em_horas": 1,
    }


def test_admin_gera_png_que_abre_e_sessao_pode_ser_revogada(client, fab):
    est = fab.est()
    fab.andar(est)
    admin = fab.token(fab.usuario(role=TipoUsuario.ADMIN))

    resposta = client.post(
        "/api/admin/simulador/sessoes", json=_payload(est.id), headers=admin,
    )
    assert resposta.status_code == 201, resposta.text
    sessao = resposta.json()
    assert sessao["estacionamento_id"] == est.id
    assert sessao["andar_numero"] == 1
    assert sessao["url"].endswith("/simulador?sessao=" + sessao["token"])

    data_url = sessao["qr_png_base64"]
    assert data_url.startswith("data:image/png;base64,")
    png = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(png)) as imagem:
        assert imagem.format == "PNG"
        assert imagem.mode == "RGB"
        assert imagem.width == imagem.height
        imagem.verify()

    token = sessao["token"]
    assert client.get(f"/api/admin/simulador/sessoes/{token}/validar").status_code == 200
    assert client.delete(f"/api/admin/simulador/sessoes/{token}", headers=admin).status_code == 200
    assert client.get(f"/api/admin/simulador/sessoes/{token}/validar").status_code == 410


def test_criacao_de_qr_exige_admin_e_local_valido(client, fab):
    est = fab.est()
    fab.andar(est)
    payload = _payload(est.id)

    assert client.post("/api/admin/simulador/sessoes", json=payload).status_code == 401
    gestor = fab.token(fab.usuario(role=TipoUsuario.GESTOR, est=est))
    assert client.post("/api/admin/simulador/sessoes", json=payload, headers=gestor).status_code == 403

    admin = fab.token(fab.usuario(role=TipoUsuario.ADMIN))
    inexistente = client.post(
        "/api/admin/simulador/sessoes", json=_payload("nao-existe"), headers=admin,
    )
    assert inexistente.status_code == 404
    andar_errado = client.post(
        "/api/admin/simulador/sessoes", json=_payload(est.id, 999), headers=admin,
    )
    assert andar_errado.status_code == 404


def test_qrcode_ausente_retorna_503_sem_criar_sessao_orfa(client, fab, monkeypatch):
    est = fab.est()
    fab.andar(est)
    admin = fab.token(fab.usuario(role=TipoUsuario.ADMIN))
    antes = {s["token"] for s in simulador_service.listar_sessoes_ativas()}

    importar_original = builtins.__import__

    def importar_sem_qrcode(nome, *args, **kwargs):
        if nome == "qrcode":
            raise ImportError("qrcode não instalado")
        return importar_original(nome, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", importar_sem_qrcode)
        resposta = client.post(
            "/api/admin/simulador/sessoes", json=_payload(est.id), headers=admin,
        )

    assert resposta.status_code == 503, resposta.text
    assert "qrcode" in resposta.json()["detail"]
    depois = {s["token"] for s in simulador_service.listar_sessoes_ativas()}
    assert depois == antes


def test_geracao_png_nao_utiliza_fabrica_de_imagem_pillow(monkeypatch):
    import qrcode

    def proibido(*_args, **_kwargs):
        raise AssertionError("A geração do QR não deve depender de qr.make_image/Pillow")

    monkeypatch.setattr(qrcode.QRCode, "make_image", proibido)
    uri = simulador_service._gerar_qr_data_url(
        "http://127.0.0.1:8081/simulador?sessao=teste",
    )
    assert uri.startswith("data:image/png;base64,")
    with Image.open(BytesIO(base64.b64decode(uri.split(",", 1)[1]))) as imagem:
        imagem.verify()
