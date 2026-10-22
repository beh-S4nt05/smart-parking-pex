#!/bin/bash
# ---------------------------------------------------------------------------
# SmartParking — dev híbrido: banco no Docker, backend LOCAL com hot-reload.
# Funciona rodado de QUALQUER lugar (âncora no diretório do próprio script,
# como faz scripts/docker.sh — lição ACH-20: nunca depender do cwd).
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"                     # → src/ (onde está o docker-compose.yml)

echo "🚀 Iniciando ambiente SmartParking (Docker: só o banco)..."

echo "1/3 Subindo PostgreSQL e PgAdmin no Docker..."
# NÃO sobe backend/nginx: quem vai atender a 8000 é o processo LOCAL abaixo
# (sobe-los junto = conflito de porta, o ACH-20 do SDD).
docker compose up -d postgres pgadmin

echo ""
echo "2/3 Aguardando banco ficar pronto (até 60s)..."
ok=0
for _ in $(seq 1 30); do
    if docker exec smartparking-postgres pg_isready -U postgres -d smartparking >/dev/null 2>&1; then
        ok=1; break
    fi
    echo "   Aguardando PostgreSQL inicializar..."
    sleep 2
done
if [ "$ok" -ne 1 ]; then
    echo "❌ PostgreSQL não respondeu em 60s — veja: docker logs smartparking-postgres"
    exit 1
fi
echo "✅ PostgreSQL pronto na 5432 (PgAdmin: http://localhost:5050 — admin@admin.com / admin)"

echo ""
echo "3/3 Backend local (venv próprio; nada de pip no Python do sistema)..."
cd backend
if [ ! -x .venv/bin/python ]; then
    echo "   Criando virtualenv .venv (primeira execução)..."
    python3 -m venv .venv
    .venv/bin/pip install -q --upgrade pip
fi
.venv/bin/pip install -q -r requirements.txt

echo ""
echo "✅ Iniciando FastAPI na porta 8000 (Ctrl+C para parar)..."
echo "📖 Swagger: http://localhost:8000/docs"
# Postgres do Docker é o banco do dev: sem fallback SQLite para .db local
# (mesma filosofia do compose: nada de "dados fantasmas" em demonstração).
export DB_AUTO_SQLITE=false
# DATABASE_URL default já aponta para postgresql+psycopg2://...@localhost:5432 ✓
# e o boot auto-repara volumes antigos (reparar_esquema_antigo — PR #15).
exec .venv/bin/python main.py
