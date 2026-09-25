# Dockerfile do backend para produção
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instala dependências Python
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

ENV PYTHONPATH=/app

# Copia código da aplicação
COPY . /app

# Corrige permissões: leitura E escrita (necessário para fallback SQLite)
RUN chmod -R a+rwX /app

# Cria usuário não-root para rodar a aplicação
RUN useradd -m appuser
USER appuser

# Expõe a porta que o Gunicorn usa
EXPOSE 8000

# Comando de inicialização com Gunicorn (múltiplos workers)
CMD ["gunicorn", "-c", "gunicorn_config.py", "main:app"]