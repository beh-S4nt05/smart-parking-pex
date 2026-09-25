# Dockerfile do backend para produção
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Cria usuário não-root para rodar a aplicação (boa prática de segurança)
RUN useradd -m appuser
USER appuser

# Expõe a porta que o Gunicorn usa
EXPOSE 8000

# Comando de inicialização com Gunicorn (múltiplos workers)
CMD ["gunicorn", "-c", "gunicorn_config.py", "main:app"]
