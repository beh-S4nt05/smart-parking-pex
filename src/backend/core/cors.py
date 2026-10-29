"""Política de CORS do navegador; não interfere em clientes nativos.

Apps React Native não fazem preflight CORS. As origens abaixo servem apenas para
a Web em desenvolvimento. Produção usa somente as origens explícitas do ambiente.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.config import Settings

DESENVOLVIMENTO_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
]

_OCTETO = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
_ROTULO = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_NOME_LOCAL = rf"{_ROTULO}(?:\.{_ROTULO})*\.(?:local|lan)"
# Expo Web usa 8081 no fluxo documentado. Não liberamos qualquer porta nem
# domínios públicos por padrão; outra porta exige CORS_ORIGINS explícito.
DESENVOLVIMENTO_LAN_ORIGIN_REGEX = (
    rf"^https?://(?:"
    rf"{_NOME_LOCAL}"
    rf"|10\.{_OCTETO}\.{_OCTETO}\.{_OCTETO}"
    rf"|192\.168\.{_OCTETO}\.{_OCTETO}"
    rf"|169\.254\.{_OCTETO}\.{_OCTETO}"
    rf"|172\.(?:1[6-9]|2\d|3[01])\.{_OCTETO}\.{_OCTETO}"
    rf"):8081$"
)


def opcoes_cors(settings: Settings) -> dict[str, Any]:
    """Retorna opções restritas e compatíveis com credenciais.

    Em desenvolvimento/teste, localhost fica na lista explícita e o IP privado
    do PC é aceito somente na porta do Expo Web. Em produção não há fallback de
    LAN nem curinga: domínios diferentes do mesmo origin devem ser declarados.
    """

    producao = settings.ENVIRONMENT.lower() == "production"
    origens = settings.CORS_ORIGINS
    if origens is None:
        origens = [] if producao else DESENVOLVIMENTO_ORIGINS

    regex = settings.CORS_ORIGIN_REGEX
    if not producao and regex is None:
        regex = DESENVOLVIMENTO_LAN_ORIGIN_REGEX

    return {
        "allow_origins": origens,
        "allow_origin_regex": regex,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
    }
