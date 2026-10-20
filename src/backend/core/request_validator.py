import hashlib
import hmac
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware que valida que as requisições de ESCRITA vêm realmente do app oficial,
    e não de Postman, scripts ou clientes modificados.

    Como funciona (somente em produção):
    - Rotas de escrita (POST/PUT/PATCH/DELETE) precisam dos headers:
        X-Request-Timestamp  -> unix time da requisição (janela de ±5 min)
        X-Request-Nonce      -> valor único por requisição (anti-replay)
        X-Request-Signature  -> HMAC-SHA256(secret, "METHOD\\nPATH\\nTS\\nNONCE\\nBODY")
    - O frontend usa exatamente a MESMA construção de string (ver
      `src/services/requestSigner.ts` do app Expo), usando HMAC de verdade.

    Em desenvolvimento/testes a validação é ignorada para facilitar a vida.
    """

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Rotas públicas e de autenticação: nunca exigem assinatura
    PUBLIC_PATHS = {
        "/",
        "/api",
        "/api/",
        "/api/status",
        "/api/health",
        "/api/version",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    AUTH_PATHS = {
        "/auth/login",
        "/auth/registrar",
        "/auth/refresh",
        "/auth/login/google",
        "/auth/login/facebook",
        "/auth/login/apple",
    }

    def __init__(self, app):
        super().__init__(app)
        self.app_secret = settings.APP_SIGNING_SECRET.encode("utf-8")
        self.timestamp_tolerance = 300  # ±5 minutos
        # nonce -> timestamp de uso (limposos automaticamente)
        self._used_nonces: dict[str, float] = {}

    # ------------------------------------------------------------------
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # GET/HEAD/OPTIONS e rotas públicas nunca são assinadas
        if (
            request.method not in self.WRITE_METHODS
            or path in self.PUBLIC_PATHS
            or path in self.AUTH_PATHS
            or path.startswith(("/docs", "/redoc", "/openapi.json"))
        ):
            return await call_next(request)

        # Em desenvolvimento/testes passa direto sem exigir assinatura
        if settings.ENVIRONMENT != "production":
            return await call_next(request)

        # ---------------- Produção: exige assinatura válida ----------------
        body = await request.body()

        error = self._validar_headers(request, path, body)
        if error is not None:
            return error

        # Devolve o body já lido para o handler do FastAPI conseguir reler.
        async def _cached_receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = _cached_receive

        return await call_next(request)

    # ------------------------------------------------------------------
    def _validar_headers(self, request: Request, path: str, body: bytes) -> JSONResponse | None:
        timestamp_header = request.headers.get("X-Request-Timestamp")
        nonce_header = request.headers.get("X-Request-Nonce")
        signature_header = request.headers.get("X-Request-Signature")

        if not timestamp_header or not nonce_header or not signature_header:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Requisição inválida: Assinatura ausente. Use o aplicativo oficial."
                },
            )

        try:
            req_timestamp = int(timestamp_header)
        except ValueError:
            return JSONResponse(
                status_code=403, content={"detail": "Timestamp inválido."}
            )

        now = time.time()
        if abs(now - req_timestamp) > self.timestamp_tolerance:
            return JSONResponse(
                status_code=403, content={"detail": "Requisição expirada."}
            )

        self._limpar_nonces_antigos(now)
        if nonce_header in self._used_nonces:
            return JSONResponse(
                status_code=403, content={"detail": "Requisição duplicada."}
            )

        # Monta a string EXATAMENTE como o frontend assina
        body_str = body.decode("utf-8") if body else ""
        path_with_query = request.url.path
        if request.url.query:
            path_with_query += f"?{request.url.query}"
        string_para_assinar = "\n".join(
            [request.method, path_with_query, timestamp_header, nonce_header, body_str]
        )

        assinatura_esperada = hmac.new(
            self.app_secret,
            string_para_assinar.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(assinatura_esperada, signature_header.strip().lower()):
            return JSONResponse(
                status_code=403,
                content={"detail": "Assinatura inválida. Acesso negado."},
            )

        # Marca o nonce como usado somente depois que a assinatura foi aceita
        self._used_nonces[nonce_header] = now
        return None

    # ------------------------------------------------------------------
    def _limpar_nonces_antigos(self, now: float):
        expirados = [
            nonce
            for nonce, ts in self._used_nonces.items()
            if now - ts > self.timestamp_tolerance
        ]
        for nonce in expirados:
            self._used_nonces.pop(nonce, None)
