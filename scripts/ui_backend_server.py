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
from fastapi.responses import JSONResponse
from main import app

RESET_TOKEN = os.environ.get("UI_TEST_RESET_TOKEN", "")
if os.environ.get("ENVIRONMENT") != "test" or not RESET_TOKEN:
    raise RuntimeError("O servidor de UI exige ENVIRONMENT=test e UI_TEST_RESET_TOKEN")


@app.post("/__ui_test/reset-rate-limit", include_in_schema=False)
async def reset_rate_limit(request: Request) -> JSONResponse:
    recebido = request.headers.get("X-UI-Test-Token", "")
    if not hmac.compare_digest(recebido, RESET_TOKEN):
        return JSONResponse(status_code=403, content={"detail": "Controle de teste inválido"})
    limiter._storage.reset()  # mesmo isolamento usado em conftest.py
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("UI_API_PORT", "8010")),
        log_level="info",
    )
