from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


def get_user_or_ip(request: Request) -> str:
    """
    Limita requisições por token JWT se o usuário estiver logado,
    ou por IP se for acesso público.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Usa o próprio token como identificador do usuário para rate limit
        # Assim cada usuário tem seu próprio limite independente do IP
        token = auth_header.split(" ")[1][:32]  # Usa só os primeiros 32 chars para economizar memória
        return f"user:{token}"
    # Se não estiver logado usa IP
    return f"ip:{get_remote_address(request)}"


# Inicializa o Limiter:
# - Em memória para desenvolvimento
# - Em produção pode ser configurado com Redis para suportar múltiplos workers/load balancer
limiter = Limiter(
    key_func=get_user_or_ip,
    default_limits=["200/minute"],  # Limite global padrão: 200 requisições por minuto por usuário/IP
    storage_uri="memory://",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handler customizado quando o limite de requisições é excedido"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Limite de requisições excedido. Aguarde um momento antes de tentar novamente.",
            "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else 60
        },
        headers={"Retry-After": str(exc.retry_after if hasattr(exc, 'retry_after') else 60)}
    )


# Limites específicos por rota:
LIMITS = {
    # Auth: Ataques de brute force são muito comuns no login - limite mais restrito
    "login": "10/minute",  # Máximo 10 tentativas de login por minuto
    "refresh": "20/minute",
    "registro": "5/minute",  # Máximo 5 cadastros por minuto por IP (anti-bots)
    # Senores: Sensores podem mandar atualizações mais frequentemente
    "atualiza_status_vaga": "60/minute",
    # Ações que escrevem no banco: limite mais baixo para evitar spam
    "criar_reserva": "30/minute",
    "pagamento": "15/minute",
    # Rotas de leitura/consulta: limite mais alto
    "consulta_publica": "120/minute",
    # Relatórios: são mais pesados, limite menor
    "relatorios": "30/minute"
}
