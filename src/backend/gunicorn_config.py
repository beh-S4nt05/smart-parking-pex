# Configuração do Gunicorn para produção
import os

# Workers: as sessões do simulador (QR) e o cache anti-replay da assinatura HMAC
# moram em memória DENTRO de cada processo. Com 2+ workers a requisição cai num
# processo que não conhece a sessão criada no outro e o QR "morre" sem motivo.
# Mantemos 1 worker enquanto o estado for em memória; para escalar, antes mover
# sessões para Redis/DB e só então subir GUNICORN_WORKERS=(2*CPU)+1 via .env.
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
worker_class = "uvicorn.workers.UvicornWorker"

# Carrega a aplicação UMA VEZ no processo master antes de criar os workers
# Evita que cada worker execute código de inicialização (como criação de tabelas) em paralelo
preload_app = True

# Bind em TODAS as interfaces. Dentro de container, "localhost:8000" escuta só o
# loopback do próprio container — o Nginx (outro container) recebe connection
# refused e devolve 502. Este era o bug central da cadeia Docker→API.
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Configurações de timeout
timeout = 120
keepalive = 5
graceful_timeout = 30

# Máximo de requisições por worker antes de reiniciar (evita vazamentos de memória)
max_requests = 1000
max_requests_jitter = (
    100  # Adiciona aleatoriedade para não reiniciar todos workers ao mesmo tempo
)

# Configurações de proxy/load balancer (NGINX por exemplo)
forwarded_allow_ips = "*"
proxy_allow_ips = "*"
x_forwarded_for_header = "X-Forwarded-For"
x_forwarded_proto_header = "X-Forwarded-Proto"

# Logs
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" tempo=%(L)ss'
)

# Previne que os workers travem em processamento longo
worker_tmp_dir = "/dev/shm"
