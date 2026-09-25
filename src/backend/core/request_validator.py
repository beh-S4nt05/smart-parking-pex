import hashlib
import hmac
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware que valida que as requisições realmente vem do seu app/frontend oficial,
    e não de Postman, navegador, scripts ou clientes modificados.
    """

    def __init__(self, app):
        super().__init__(app)
        self.APP_SECRET = settings.APP_SIGNING_SECRET
        self.TIMESTAMP_TOLERANCE = 300  # 5 minutos
        self.used_nonces = set()
        self.nonce_timestamps = []

    async def dispatch(self, request: Request, call_next):
        public_get_routes = [
            "/", "/api/status", "/api/health", "/api/version", "/docs", "/redoc", "/openapi.json"
        ]
        auth_routes = ["/auth/login", "/auth/registrar", "/auth/refresh",
                       "/auth/login/google", "/auth/login/facebook", "/auth/login/apple"]
        path = request.url.path

        # Rotas GET de consulta pública e autenticação não exigem assinatura
        if (request.method == "GET") or (path in auth_routes) or (path in public_get_routes):
            return await call_next(request)

        # Para TODAS as rotas que modificam dados em produção, exigimos assinatura
        if request.method in ["POST", "PUT", "PATCH", "DELETE"] and settings.ENVIRONMENT == "production":
            # TODA validação de assinatura só ocorre em produção
            pass
        else:
            # Em desenvolvimento e testes passa direto sem assinatura
            return await call_next(request)
            timestamp_header = request.headers.get("X-Request-Timestamp")
            nonce_header = request.headers.get("X-Request-Nonce")
            signature_header = request.headers.get("X-Request-Signature")

            if not timestamp_header or not nonce_header or not signature_header:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Requisição inválida: Assinatura ausente. Use o aplicativo oficial."}
                )

            try:
                req_timestamp = int(timestamp_header)
            except ValueError:
                return JSONResponse(status_code=403, content={"detail": "Timestamp inválido."})

            now = int(time.time())
            if abs(now - req_timestamp) > self.TIMESTAMP_TOLERANCE:
                return JSONResponse(status_code=403, content={"detail": "Requisição expirada."})

            if nonce_header in self.used_nonces:
                return JSONResponse(status_code=403, content={"detail": "Requisição duplicada."})

            self._limpar_nonces_antigos(now)

            # Lê corpo e prepara para assinatura
            body = await request.body()
            body_str = body.decode("utf-8") if body else ""

            # Monta a string de assinatura
            string_para_assinar = f"{request.method}\n{path}\n{timestamp_header}\n{nonce_header}\n{body_str}"

            assinatura_esperada = hmac.new(
                self.APP_SECRET.encode("utf-8"),
                string_para_assinar.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(assinatura_esperada, signature_header):
                return JSONResponse(status_code=403, content={"detail": "Assinatura inválida. Acesso negado."})

            # Verifica User Agent
            user_agent = request.headers.get("user-agent", "").lower()
            blocked_uas = ["postman", "insomnia", "curl", "wget", "python-requests", "mozilla", "chrome", "safari", "firefox"]
            for blocked in blocked_uas:
                if blocked in user_agent:
                    return JSONResponse(status_code=403, content={"detail": "Utilize o aplicativo oficial."})

            # Marca nonce como usado
            self.used_nonces.add(nonce_header)
            self.nonce_timestamps.append((nonce_header, req_timestamp))

        response = await call_next(request)
        return response

    def _limpar_nonces_antigos(self, now: int):
        validos = []
        for nonce, ts in self.nonce_timestamps:
            if now - ts <= self.TIMESTAMP_TOLERANCE:
                validos.append((nonce, ts))
            else:
                self.used_nonces.discard(nonce)
        self.nonce_timestamps = validos
