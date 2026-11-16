"""
Sessões do simulador de sensores via QR.

O admin (web) gera uma sessão para um estacionamento/andar; o backend devolve
uma URL tokenizada + imagem QR (base64). O celular abre a URL, o motorista/admin
faz login no app e a tela do simulador valida o token da sessão antes de liberar
as operações de escrita.

⚠️ Armazenamos as sessões em memória (por processo) — sufixa para o piloto e
para a apresentação. Com múltiplos workers em produção, mover para Redis/Postgres.
"""

import base64
import struct
import zlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from models.db_models import Andar, Estacionamento

EXPIRACAO_PADRAO_HORAS = 12

# token -> sessão
_SESSOES: dict[str, dict] = {}


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _expirados(salvar: dict) -> bool:
    expira_em = salvar.get("expira_em")
    return bool(expira_em and _agora() > expira_em)


def criar_sessao(
    db,
    estacionamento_id: str,
    andar_numero: int | None = None,
    expira_em_horas: int = EXPIRACAO_PADRAO_HORAS,
    base_url: str = "",
) -> dict:
    est = db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estacionamento não encontrado",
        )

    andar = None
    if andar_numero is not None:
        andar = (
            db.query(Andar)
            .filter(Andar.estacionamento_id == est.id, Andar.numero_andar == andar_numero)
            .first()
        )
        if not andar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Andar não encontrado neste estacionamento",
            )

    token = secrets.token_urlsafe(8)  # ~13 chars — URL curta, cabe no QR
    expira_em = _agora() + timedelta(hours=max(1, min(expira_em_horas, 48)))

    sessao = {
        "token": token,
        "estacionamento_id": est.id,
        "estacionamento_nome": est.nome,
        "andar_numero": andar.numero_andar if andar else None,
        "andar_id": andar.id if andar else None,
        "criada_em": _agora(),
        "expira_em": expira_em,
    }
    url = base_url.rstrip("/") + f"/simulador?sessao={token}" if base_url else None
    # Gerar o QR antes de publicar o token: falhas não deixam sessões órfãs.
    qr_png_base64 = _gerar_qr_data_url(url) if url else None
    _SESSOES[token] = sessao

    return {
        **_publicar(sessao),
        "url": url,
        "qr_png_base64": qr_png_base64,
    }


def _publicar(sessao: dict) -> dict:
    return {
        "token": sessao["token"],
        "estacionamento_id": sessao["estacionamento_id"],
        "estacionamento_nome": sessao["estacionamento_nome"],
        "andar_numero": sessao["andar_numero"],
        "criada_em": sessao["criada_em"].isoformat(),
        "expira_em": sessao["expira_em"].isoformat(),
    }


def validar_sessao(token: str) -> dict:
    sessao = _SESSOES.get(token)
    if not sessao or _expirados(sessao):
        _SESSOES.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Sessão do simulador expirada ou revogada. Gere um novo QR no painel.",
        )
    return _publicar(sessao)


def listar_sessoes_ativas() -> list[dict]:
    agora = _agora()
    mortos = [t for t, s in _SESSOES.items() if _expirados(s)]
    for t in mortos:
        _SESSOES.pop(t, None)
    ativas = sorted(_SESSOES.values(), key=lambda s: s["criada_em"], reverse=True)
    return [
        {
            **_publicar(s),
            "expira_em_horas_restantes": round(
                (s["expira_em"] - agora).total_seconds() / 3600, 1
            ),
        }
        for s in ativas
    ]


def revogar_por_estacionamento(estacionamento_id: str) -> int:
    """Derruba as sessões QR da filial quando ela é excluída (chamado pelo
    purge do admin_service). Retorna quantas sessões morreram."""
    mortas = 0
    for tok in list(_SESSOES.keys()):
        if _SESSOES[tok].get("estacionamento_id") == estacionamento_id:
            _SESSOES.pop(tok, None)
            mortas += 1
    return mortas


def revogar_sessao(token: str) -> dict:
    if token not in _SESSOES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada (já expirada ou revogada)",
        )
    _SESSOES.pop(token)
    return {"mensagem": "Sessão revogada — o link do celular não funciona mais"}


def _png_chunk(tipo: bytes, conteudo: bytes) -> bytes:
    """Um chunk PNG com comprimento e CRC32 (somente biblioteca padrão)."""
    return (
        struct.pack("!I", len(conteudo))
        + tipo
        + conteudo
        + struct.pack("!I", zlib.crc32(tipo + conteudo) & 0xFFFFFFFF)
    )


def _gerar_qr_data_url(texto: str) -> str:
    """
    Gera um PNG RGB válido diretamente da matriz QR, sem depender do Pillow.

    No ambiente local, qrcode pode estar instalado enquanto Pillow não está;
    chamar qr.make_image() nessa situação levantava ImportError e a rota POST
    /api/admin/simulador/sessoes devolvia HTTP 500.
    """
    try:
        import qrcode
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geração de QR indisponível: instale as dependências do backend (qrcode).",
        ) from exc

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,  # zona de silêncio recomendada para leitura pela câmera
    )
    qr.add_data(texto)
    qr.make(fit=True)

    matriz = qr.get_matrix()  # inclui a borda branca
    escala = 8
    escuro, claro = b"\x0f\x17\x2a", b"\xff\xff\xff"
    linhas_png = b"".join(
        (b"\x00" + b"".join((escuro if modulo else claro) * escala for modulo in linha)) * escala
        for linha in matriz
    )
    largura = len(matriz[0]) * escala
    altura = len(matriz) * escala
    cabecalho = struct.pack("!IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", cabecalho)
        + _png_chunk(b"IDAT", zlib.compress(linhas_png))
        + _png_chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
