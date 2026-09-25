# Configuração do Gunicorn para produção com Load Balancing
import multiprocessing
import os

# Número de workers: regra geral é (2 * núcleos_CPU) + 1
# Cada worker é um processo separado que lida com requisições, distribuindo a carga automaticamente
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# Carrega a aplicação UMA VEZ no processo master antes de criar os workers
# Evita que cada worker execute código de inicialização (como criação de tabelas) em paralelo
preload_app = True


# Bind em todas as interfaces na porta 8000
bind = os.getenv("GUNICORN_BIND", "localhost:8000")

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
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" tempo=%(L)ss'
)

# Previne que os workers travem em processamento longo
worker_tmp_dir = "/dev/shm"
