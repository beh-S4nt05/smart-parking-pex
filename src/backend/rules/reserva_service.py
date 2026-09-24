from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.db_models import Reserva, Vaga, StatusVaga, StatusReserva, Usuario, Andar
from models.schemas import ReservaCreate


def criar_reserva(db: Session, dados: ReservaCreate, usuario_logado: Usuario) -> Reserva:
    """
    Cria uma nova reserva:
    1. Verifica se a vaga existe
    2. Verifica se a vaga está livre
    3. Atualiza status da vaga para RESERVADA
    4. Cria o registro de reserva
    """
    vaga = db.query(Vaga).filter(Vaga.id == dados.vaga_id).first()
    if not vaga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada"
        )

    if vaga.status != StatusVaga.LIVRE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta vaga não está disponível para reserva"
        )

    if dados.horario_fim <= dados.horario_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Horário de fim deve ser posterior ao horário de início"
        )

    # Cria a reserva
    nova_reserva = Reserva(
        **dados.model_dump(),
        usuario_id=usuario_logado.id,
        status=StatusReserva.CONFIRMADA
    )

    # Atualiza status da vaga
    vaga.status = StatusVaga.RESERVADA

    db.add(nova_reserva)
    db.commit()
    db.refresh(nova_reserva)

    # Adiciona dados do andar na vaga da resposta
    andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
    if andar:
        vaga.numero_andar = andar.numero_andar
    nova_reserva.vaga = vaga

    return nova_reserva


def cancelar_reserva(db: Session, reserva_id: str, usuario_logado: Usuario) -> Reserva:
    """
    Cancela uma reserva e libera a vaga imediatamente.
    Apenas o dono da reserva pode cancelar.
    """
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva não encontrada"
        )

    if reserva.usuario_id != usuario_logado.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para cancelar esta reserva"
        )

    if reserva.status == StatusReserva.CANCELADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reserva já está cancelada"
        )

    # Atualiza status da reserva
    reserva.status = StatusReserva.CANCELADA

    # Libera a vaga se ela ainda estava reservada
    vaga = db.query(Vaga).filter(Vaga.id == reserva.vaga_id).first()
    if vaga and vaga.status == StatusVaga.RESERVADA:
        vaga.status = StatusVaga.LIVRE

    db.commit()
    db.refresh(reserva)

    # Adiciona dados da vaga
    if vaga:
        andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
        if andar:
            vaga.numero_andar = andar.numero_andar
        reserva.vaga = vaga

    return reserva


def listar_reservas_usuario(db: Session, usuario_id: str) -> List[Reserva]:
    """Lista todas as reservas de um usuário específico"""
    reservas = db.query(Reserva).filter(Reserva.usuario_id == usuario_id).all()

    # Adiciona dados do andar em cada vaga
    for reserva in reservas:
        if reserva.vaga:
            andar = db.query(Andar).filter(Andar.id == reserva.vaga.andar_id).first()
            if andar:
                reserva.vaga.numero_andar = andar.numero_andar

    return reservas
