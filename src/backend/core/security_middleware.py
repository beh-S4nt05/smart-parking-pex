from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import re
from typing import Set, Dict
import time
from collections import defaultdict


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que adiciona todos os headers de segurança recomendados e bloqueia acesso indevido"""

    # Padrões comuns de SQL Injection para detectar e bloquear automaticamente
    SQL_INJECTION_PATTERNS = [
        re.compile(
            r"(?i)(\b(select|insert|update|delete|drop|alter|create|truncate|exec|union|into|load_file|outfile)\b)"
        ),
        re.compile(r"(?i)(--\s|\bor\b\s+\d+\s*=\s*\d+|\band\b\s+\d+\s*=\s*\d+)"),
        re.compile(r"(?i)(\'|\"|;|--|/\*|\*/|xp_|sp_)"),
        re.compile(r"(?i)(union(\s|\+)+select|select(\s|\+)+from)", re.IGNORECASE),
        re.compile(
            r"(?i)script\s*>", re.IGNORECASE
        ),  # Proteção contra XSS básico em parâmetros
        re.compile(r"(?i)(javascript:|onerror=|onload=|eval\()", re.IGNORECASE),
    ]

    # User agents de scanners automatizados que costumam atacar APIs
    BLOCKED_AGENTS = {
        "sqlmap",
        "nikto",
        "nmap",
        "masscan",
        "dirbuster",
        "wpscan",
        "acunetix",
        "burpsuite",
        "zaproxy",
        "vulnerability-scanner",
    }

    def __init__(self, app, environment: str = "development"):
        super().__init__(app)
        self.environment = environment
        # Rastreamento de requisições para anti-duplicação/abuso (simples em memória)
        # Para produção com múltiplos workers use Redis
        self.request_tracker: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Em desenvolvimento desativa anti-duplicação para facilitar testes
        if self.environment != "production":
            return await call_next(request)

        # 1. Bloqueia scanners automatizados pelo User-Agent
        user_agent = request.headers.get("user-agent", "").lower()
        for blocked_agent in self.BLOCKED_AGENTS:
            if blocked_agent in user_agent:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Acesso não autorizado: Scanner detectado"},
                )

        # 2. Verifica se não está tentando acessar endpoints que não existem com método HEAD/OPTIONS bloqueado
        # (evita scaneamento automatizado de rotas)
        if request.method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}:
            return JSONResponse(
                status_code=405, content={"detail": "Método não permitido"}
            )

        # 3. Proteção contra SQL Injection: verifica TODOS os parâmetros de query e body
        client_ip = request.client.host if request.client else "unknown"
        await self._verificar_sql_injection(request)

        # 4. Anti-duplicação de requisições: bloqueia requisições idênticas feitas em menos de 1s
        # Evita cliques duplicados e ataques de repetição
        request_key = (
            f"{client_ip}:{request.method}:{request.url.path}:{await request.body()}"
        )
        agora = time.time()
        # Limpa registros antigos (mais de 1 segundo)
        self.request_tracker[client_ip] = [
            t for t in self.request_tracker[client_ip] if agora - t < 1
        ]

        # Verifica se essa requisição foi feita muito recentemente
        if (
            len(self.request_tracker[client_ip]) >= 5
        ):  # Mais de 5 requisições por segundo
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Muitas requisições. Aguarde um momento e tente novamente."
                },
            )

        self.request_tracker[client_ip].append(agora)

        # 5. Processa a requisição normalmente
        response: Response = await call_next(request)

        # 6. Adiciona headers de segurança em TODAS as respostas
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'",
            "Permissions-Policy": "geolocation=(self), microphone=()",
            "Strict-Transport-Security": (
                "max-age=31536000; includeSubDomains"
                if self.environment == "production"
                else ""
            ),
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Server": "SmartParking API",  # Esconde o cabeçalho Server padrão do Uvicorn
            "X-Powered-By": "",  # Remove cabeçalho que expõe tecnologia
        }

        for header, valor in security_headers.items():
            if valor:
                response.headers[header] = valor

        # Remove headers que expõem informações do servidor
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        if "server" in response.headers:
            del response.headers["server"]

        return response

    async def _verificar_sql_injection(self, request: Request):
        """Verifica todos os parâmetros da requisição por tentativas de SQL Injection"""
        # Verifica parâmetros de query string
        for chave, valor in request.query_params.items():
            if self._contem_sql_injection(valor):
                raise JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Requisição inválida: Caracteres não permitidos detectados"
                    },
                )

        # Verifica path parameters
        for valor in request.path_params.values():
            if isinstance(valor, str) and self._contem_sql_injection(valor):
                raise JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Requisição inválida: Caracteres não permitidos detectados"
                    },
                )

        # Verifica corpo da requisição (se for JSON/form)
        from fastapi.responses import JSONResponse

        if request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.json()
                    res = await self._verificar_objeto_injection(body)
                    if res is not None:
                        raise res
                except JSONResponse:
                    raise
                except Exception:
                    # Se não for JSON válido deixa passar pra validação do Pydantic tratar
                    pass

    def _contem_sql_injection(self, texto: str) -> bool:
        """Verifica se um texto contém padrões de SQL Injection/XSS"""
        if not isinstance(texto, str):
            return False
        for padrao in self.SQL_INJECTION_PATTERNS:
            if padrao.search(texto):
                return True
        return False

    async def _verificar_objeto_injection(self, obj):
        """Percorre recursivamente o JSON do corpo verificando injection"""
        from fastapi.responses import JSONResponse

        if isinstance(obj, dict):
            for valor in obj.values():
                res = await self._verificar_objeto_injection(valor)
                if res is not None:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = await self._verificar_objeto_injection(item)
                if res is not None:
                    return res
        elif isinstance(obj, str):
            if self._contem_sql_injection(obj):
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Requisição inválida: Caracteres não permitidos detectados"
                    },
                )
        return None
