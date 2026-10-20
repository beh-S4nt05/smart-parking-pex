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
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

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
    andar_numero: Optional[int] = None,
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
    _SESSOES[token] = sessao

    url = base_url.rstrip("/") + f"/simulador?sessao={token}" if base_url else None

    return {
        **_publicar(sessao),
        "url": url,
        "qr_png_base64": _gerar_qr_data_url(url) if url else None,
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


def revogar_sessao(token: str) -> dict:
    if token not in _SESSOES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada (já expirada ou revogada)",
        )
    _SESSOES.pop(token)
    return {"mensagem": "Sessão revogada — o link do celular não funciona mais"}


def _gerar_qr_data_url(texto: str) -> Optional[str]:
    """
    Desenha o QR Code no backend e devolve um data URL PNG — o app mostra com
    <Image source={{uri}}> sem precisar de dependência nova no frontend.
    """
    try:
        import qrcode  # aditivo em requirements.txt; se faltar, o app só não mostra a imagem
    except ImportError:
        return None

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(texto)
    qr.make(fit=True)
    imagem = qr.make_image(fill_color="#0F172A", back_color="white")

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
