"""Servidor exclusivo das jornadas E2E, com isolamento do rate limiter.

Este módulo nunca é importado por ``main:app`` em produção. O endpoint de
controle exige ENVIRONMENT=test e um token local, e apenas restaura o estado
entre testes; os limites continuam ativos durante cada jornada.
"""

from __future__ import annotations

import hmac
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "backend"))

import uvicorn
from core.rate_limiter import limiter
from fastapi import Request
from models.database import SessionLocal
from models.schemas import LoginRequest
from rules import auth_service
from fastapi.responses import JSONResponse
from main import app

RESET_TOKEN = os.environ.get("UI_TEST_RESET_TOKEN", "")
if os.environ.get("ENVIRONMENT") != "test" or not RESET_TOKEN:
    raise RuntimeError("O servidor de UI exige ENVIRONMENT=test e UI_TEST_RESET_TOKEN")


# Esta rota de QA não existe na aplicação main:app, e o servidor E2E
# somente escuta loopback. O teste autentica com o MESMO serviço real, mas não
# esgota a cota de /auth/login; auth.spec.ts continua testando o login normal.
_CONTAS_QA = frozenset({
    "admin@smartparking.com",
    "gestor@smartparking.com",
    "financeiro@smartparking.com",
    "motorista@smartparking.com",
})


@app.post("/__ui_test/session", include_in_schema=False)
async def sessao_de_teste(request: Request) -> JSONResponse:
    recebido = request.headers.get("X-UI-Test-Token", "")
    if not hmac.compare_digest(recebido, RESET_TOKEN):
        return JSONResponse(status_code=403, content={"detail": "Controle de teste inválido"})
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "JSON inválido"})
    if not isinstance(payload, dict) or payload.get("email") not in _CONTAS_QA:
        return JSONResponse(status_code=403, content={"detail": "Conta fora do seed QA"})
    credenciais = LoginRequest(email=payload["email"], senha=payload.get("senha", ""))
    db = SessionLocal()
    try:
        sessao = auth_service.autenticar_usuario(db, credenciais, "playwright-fixture")
        return JSONResponse(sessao.model_dump(mode="json"))
    finally:
        db.close()


@app.post("/__ui_test/reset-rate-limit", include_in_schema=False)
async def reset_rate_limit(request: Request) -> JSONResponse:
    recebido = request.headers.get("X-UI-Test-Token", "")
    if not hmac.compare_digest(recebido, RESET_TOKEN):
        return JSONResponse(status_code=403, content={"detail": "Controle de teste inválido"})
    limiter.reset()  # API pública: limpa as janelas do backend apenas em testes
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.environ.get("UI_API_PORT", "8010")),
        log_level="info",
    )
