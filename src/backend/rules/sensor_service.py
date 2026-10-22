"""
Sensores físicos (RF-45 · ADR-03) — chave por dispositivo, ingestão idempotente.

O dispositivo NÃO faz login JWT: apresenta `X-Device-Key`; guardamos apenas o
SHA-256 da chave. Emissão/revogação são exclusivas do admin global (mesma
família de decisão do simulador). A idempotência (sensor_id, seq) protege de
retransmissão de rede: o MESMO seq reenviado é contabilizado como duplicado e
não gera segunda estadia no Histórico.
"""

import hashlib
import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.timeutils import utc_agora
from models.db_models import (
    Andar,
    Estacionamento,
    Sensor,
    SensorEvento,
    StatusVaga,
    Vaga,
)
from models.schemas import VagaAtualizaStatus
from rules import vaga_service

VALIDOS = {StatusVaga.OCUPADA.value, StatusVaga.LIVRE.value}


def _hash(chave: str) -> str:
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


def emitir_sensor(db: Session, estacionamento_id: str, codigo: str, nome: str | None = None):
    """Cria o dispositivo e devolve (sensor, chave_clara) — a chave NÃO é
    armazenada em claro nem recuperável: perdida → revogar e reemitir."""
    est = db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estacionamento não encontrado")
    codigo = (codigo or "").strip().upper()
    if not codigo:
        raise HTTPException(status_code=422, detail="codigo é obrigatório (ex.: SNS-A01)")
    if db.query(Sensor).filter(Sensor.codigo == codigo).first():
        raise HTTPException(status_code=409, detail=f"Já existe um sensor com o código {codigo}")
    chave = f"SPK-{secrets.token_urlsafe(24)}"
    sensor = Sensor(
        estacionamento_id=est.id, codigo=codigo, nome=nome or f"Sensor {codigo}",
        chave_hash=_hash(chave), ativo=True,
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor, chave


def autenticar_chave(db: Session, chave: str) -> Sensor:
    if not chave:
        raise HTTPException(status_code=401, detail="X-Device-Key ausente")
    sensor = db.query(Sensor).filter(
        Sensor.chave_hash == _hash(chave), Sensor.ativo.is_(True)
    ).first()
    if not sensor:
        raise HTTPException(status_code=401, detail="Chave de dispositivo inválida ou revogada")
    return sensor


def registrar_eventos(db: Session, sensor: Sensor, eventos: list[dict]) -> dict:
    """Aplica um lote; retorna {aceitos, duplicados, ignorados, erros[]}."""
    aceitos = duplicados = ignorados = 0
    erros: list[str] = []
    agora = utc_agora()
    for i, ev in enumerate(eventos):
        seq = ev.get("seq")
        codigo_vaga = (ev.get("codigo_vaga") or "").strip().upper()
        novo_status = ev.get("status")
        if seq is None or not codigo_vaga or not novo_status:
            erros.append(f"evento {i}: faltam seq/codigo_vaga/status")
            ignorados += 1
            continue
        if novo_status not in VALIDOS:
            erros.append(f"evento {i}: status '{novo_status}' inválido (use livre|ocupada)")
            ignorados += 1
            continue
        # idempotência: mesmo (sensor, seq) já registrado → skip silencioso
        if db.query(SensorEvento.id).filter(
            SensorEvento.sensor_id == sensor.id, SensorEvento.seq == int(seq)
        ).first():
            # a constraint (sensor_id, seq) É a idempotência: registramos o
            # 1º evento e só contamos o reenvio — reinserir violaria a chave.
            duplicados += 1
            continue
        # resolve a vaga pelo código DENTRO do estacionamento do sensor
        vagas = (
            db.query(Vaga)
            .join(Andar, Vaga.andar_id == Andar.id)
            .filter(Andar.estacionamento_id == sensor.estacionamento_id)
            .filter(Vaga.codigo == codigo_vaga)
            .all()
        )
        if not vagas:
            erros.append(f"evento {i}: vaga {codigo_vaga} não existe no estacionamento do sensor")
            db.add(SensorEvento(sensor_id=sensor.id, vaga_id=None, seq=int(seq),
                                status_enviado=novo_status, aplicado=False, ocorrido_em=agora))
            db.commit()
            ignorados += 1
            continue
        if len(vagas) > 1:
            erros.append(f"evento {i}: código {codigo_vaga} ambíguo em andares distintos — rejeitado")
            db.add(SensorEvento(sensor_id=sensor.id, vaga_id=None, seq=int(seq),
                                status_enviado=novo_status, aplicado=False, ocorrido_em=agora))
            db.commit()
            ignorados += 1
            continue
        vaga = vagas[0]
        try:
            vaga_service.atualizar_status_vaga(
                db, vaga.id, VagaAtualizaStatus(status=novo_status, origem="sensor")
            )
        except HTTPException as exc:
            erros.append(f"evento {i}: {exc.detail}")
            db.add(SensorEvento(sensor_id=sensor.id, vaga_id=vaga.id, seq=int(seq),
                                status_enviado=novo_status, aplicado=False, ocorrido_em=agora))
            db.commit()
            ignorados += 1
            continue
        db.add(SensorEvento(sensor_id=sensor.id, vaga_id=vaga.id, seq=int(seq),
                           status_enviado=novo_status, aplicado=True, ocorrido_em=agora))
        db.commit()
        aceitos += 1
    sensor.ultimo_evento_em = agora
    db.commit()
    return {"aceitos": aceitos, "duplicados": duplicados, "ignorados": ignorados, "erros": erros}
