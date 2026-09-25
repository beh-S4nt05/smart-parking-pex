#!/bin/bash
echo "🚀 Iniciando ambiente SmartParking com Docker..."

echo "1/3 Subindo banco de dados PostgreSQL no Docker..."
docker compose up -d

echo ""
echo "2/3 Aguardando banco ficar pronto..."
until docker exec smartparking-postgres pg_isready -U postgres -d smartparking > /dev/null 2>&1; do
    echo "   Aguardando PostgreSQL inicializar..."
    sleep 2
done
echo "✅ PostgreSQL está pronto na porta 5432"

echo ""
echo "3/3 Instalando dependências do backend e iniciando servidor..."
cd src/backend
pip3 install -q -r requirements.txt

echo ""
echo "✅ Iniciando FastAPI na porta 8000..."
echo "📖 Documentação Swagger: http://localhost:8000/docs"
echo "🔍 PgAdmin (gerenciador do banco): http://localhost:5050 (admin@admin.com / admin)"
echo ""
python3 main.py
