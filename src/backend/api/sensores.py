"""
Ingestão de eventos de sensores (RF-45/ADR-03) — SEM JWT: o dispositivo
apresenta `X-Device-Key`. Rate limit por IP bem folgado (dispositivos falam
muito), idempotência por (sensor, seq).
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.rate_limiter import LIMITS, limiter
from models.database import get_db
from rules import sensor_service

router = APIRouter(prefix="/sensores", tags=["Sensores IoT"])


class EventoVagaIn(BaseModel):
    seq: int = Field(ge=0, description="sequencial por dispositivo (idempotência)")
    codigo_vaga: str
    status: str = Field(description="livre | ocupada")
    ocorreu_em: Optional[datetime] = None


class LoteEventosIn(BaseModel):
    eventos: List[EventoVagaIn] = Field(min_length=1, max_length=200)


@router.post("/eventos")
@limiter.limit(LIMITS["sensores"])
async def receber_eventos(
    request: Request,
    dados: LoteEventosIn,
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key"),
    db: Session = Depends(get_db),
):
    """
    `POST /api/sensores/eventos` — corpo {"eventos":[{"seq":1,"codigo_vaga":"A01",
    "status":"ocupada"}]}. Aplica via vaga_service (abre/fecha Histórico, origem
    "sensor") e responde {aceitos, duplicados, ignorados, erros[]}.
    """
    sensor = sensor_service.autenticar_chave(db, x_device_key or "")
    resultado = sensor_service.registrar_eventos(
        db, sensor, [e.model_dump() for e in dados.eventos]
    )
    return resultado
