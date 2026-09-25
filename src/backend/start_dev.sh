#!/bin/bash
echo "🚀 Iniciando backend SmartParking em ambiente de desenvolvimento"
echo "📖 Documentação Swagger disponível em http://localhost:8000/docs"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
