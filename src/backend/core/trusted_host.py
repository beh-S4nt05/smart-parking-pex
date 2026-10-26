"""TrustedHost com suporte a curingas de IP privado usados na LAN.

O Starlette aceita ``*.dominio.com``, mas versões atuais rejeitam padrões como
``192.168.*.*`` na construção do middleware. Como a stack é montada no primeiro
request, um padrão desses transformava TODA resposta de produção em 500.

Aqui os padrões de IP ficam fora da validação do Starlette e só podem liberar
um Host que seja um IP literal válido. Domínios, IPs exatos e ``*.dominio``
continuam sendo validados pela implementação oficial, sem abrir ``*``.
"""

import fnmatch
import ipaddress
import re

from starlette.datastructures import Headers
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


class TrustedHostLANMiddleware(TrustedHostMiddleware):
    def __init__(self, app: ASGIApp, allowed_hosts=None, www_redirect: bool = True):
        allowed_hosts = list(allowed_hosts or [])
        self.ip_wildcards = [
            pattern.lower() for pattern in allowed_hosts if _is_ip_wildcard(pattern)
        ]
        domain_hosts = [
            pattern for pattern in allowed_hosts if not _is_ip_wildcard(pattern)
        ]
        super().__init__(
            app, allowed_hosts=domain_hosts, www_redirect=www_redirect
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.ip_wildcards and scope["type"] in ("http", "websocket"):
            host = _literal_ip_host(Headers(scope=scope).get("host"))
            if host and any(
                fnmatch.fnmatchcase(host, pattern) for pattern in self.ip_wildcards
            ):
                await self.app(scope, receive, send)
                return
        await super().__call__(scope, receive, send)


def _is_ip_wildcard(pattern: str) -> bool:
    """Distingue ``192.168.*.*`` de curingas de domínio/valores inválidos."""
    return (
        "*" in pattern
        and pattern != "*"
        and not pattern.startswith("*.")
        and re.fullmatch(r"[0-9A-Fa-f:.*]+", pattern) is not None
    )


def _literal_ip_host(host_header: str | None) -> str | None:
    """Extrai somente IP literal de Host, recusando porta/usuário malformados."""
    if not host_header:
        return None
    match = re.fullmatch(
        r"(?P<host>\[[0-9A-Fa-f:.]+\]|[^:\[\]]+)(?::(?P<port>\d{1,5}))?",
        host_header,
    )
    if not match:
        return None
    port = match.group("port")
    if port is not None and int(port) > 65535:
        return None
    candidate = match.group("host").removeprefix("[").removesuffix("]")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None
