"""Trilha de decisões sensíveis sem registrar URL bruta, token ou dados pessoais.

O middleware observa a RESPOSTA do servidor, não a alegação de permissão no app.
Uma falha de auditoria não derruba o piloto; em produção, use fila e alerta.
"""
import re

from starlette.middleware.base import BaseHTTPMiddleware

# Regras explícitas: nunca persista URL completa ou query string (podem trazer tokens).
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F-]{20,}$")
MAX_EVENTS_IN_QUERY = 100


def _operacao_segura(path: str) -> str:
    partes = path.split("/")
    normalizadas = []
    for parte in partes:
        if not parte:
            continue
        if parte.isdigit() or _UUID.fullmatch(parte) or len(parte) > 36:
            normalizadas.append("{id}")
        else:
            # Nenhum path arbitrário é persistido: só conservamos prefixos fixos.
            normalizadas.append(parte if parte in {
                "auth", "login", "registrar", "refresh", "me", "senha", "logout",
                "api", "admin", "usuarios", "estacionamentos", "vagas", "reservas",
                "pagamentos", "sessoes", "sensores", "eventos", "seguranca",
                "credenciais", "mfa", "redefinir", "email", "confirmar",
                "lote", "status", "revogar", "revogar-todas", "ativar-desativar",
                "promover-admin", "reset-senha", "avaliar", "solicitar",
            } else "{id}")
    return "/" + "/".join(normalizadas)[:64]


def _categoria(path: str, status_code: int, method: str) -> str | None:
    if path.startswith("/api/sensores/") and status_code >= 400:
        return "sensor_negado"
    if path.startswith("/auth/") and status_code in {401, 403, 429}:
        return "autenticacao_negada"
    if path.startswith("/api/admin/") and status_code in {401, 403}:
        return "acesso_negado"
    if path.startswith("/api/admin/") and method in {"POST", "PUT", "PATCH", "DELETE"} and 200 <= status_code < 300:
        return "operacao_admin"
    if path.startswith("/api/") and status_code in {401, 403}:
        return "acesso_negado"
    return None


def _identidade_autenticada(authorization: str) -> str | None:
    if not authorization.lower().startswith("bearer "):
        return None
    try:
        from core.security import decodificar_token
        payload = decodificar_token(authorization.split(" ", 1)[1].strip())
        return payload.get("sub") if payload.get("type") == "access" else None
    except Exception:
        return None


def registrar_evento(db, *, usuario_id: str | None, categoria: str,
                     operacao: str, metodo: str, status_http: int,
                     estacionamento_id: str | None = None) -> None:
    """Uso por camadas de serviço: aceita somente rótulos internos, nunca payload."""
    from models.db_models import EventoSeguranca

    db.add(EventoSeguranca(
        usuario_id=usuario_id, estacionamento_id=estacionamento_id,
        categoria=categoria[:32], operacao=_operacao_segura(operacao),
        metodo=metodo[:8], status_http=status_http,
    ))
    db.commit()


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        categoria = _categoria(path, response.status_code, request.method)
        if categoria:
            try:
                from models.database import SessionLocal
                with SessionLocal() as db:
                    registrar_evento(
                        db, usuario_id=_identidade_autenticada(
                            request.headers.get("Authorization", "")
                        ), categoria=categoria, operacao=path,
                        metodo=request.method, status_http=response.status_code,
                    )
            except Exception:
                # Não esconder falha: sinal visível no servidor para o operador.
                import logging
                logging.getLogger("smartparking.security").exception(
                    "Falha na auditoria de evento HTTP sensível"
                )
        return response
