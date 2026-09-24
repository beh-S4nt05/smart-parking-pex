from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.db_models import Vaga, StatusVaga, Historico, Andar
from models.schemas import VagaCreate, VagaAtualizaStatus


def buscar_vaga_por_id(db: Session, vaga_id: str) -> Optional[Vaga]:
    """Busca uma vaga pelo ID UUID"""
    return db.query(Vaga).filter(Vaga.id == vaga_id).first()


def criar_vaga(db: Session, dados: VagaCreate) -> Vaga:
    """Cria uma nova vaga em um andar"""
    # Verifica se andar existe
    andar = db.query(Andar).filter(Andar.id == dados.andar_id).first()
    if not andar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Andar não encontrado"
        )

    nova_vaga = Vaga(**dados.model_dump())
    db.add(nova_vaga)
    db.commit()
    db.refresh(nova_vaga)
    return nova_vaga


def atualizar_status_vaga(
    db: Session,
    vaga_id: str,
    dados: VagaAtualizaStatus
) -> Vaga:
    """
    Atualiza o status de uma vaga e cria registro de histórico automaticamente
    quando muda para ocupada ou livre (entrada/saída de veículo).
    """
    vaga = buscar_vaga_por_id(db, vaga_id)
    if not vaga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada"
        )

    status_anterior = vaga.status
    novo_status = dados.status

    andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
    estacionamento_id = andar.estacionamento_id if andar else None

    # Registra entrada quando a vaga passa a ser ocupada
    if novo_status == StatusVaga.OCUPADA and status_anterior == StatusVaga.LIVRE:
        registro = Historico(
            estacionamento_id=estacionamento_id,
            vaga_id=vaga.id,
            entrada_em=datetime.utcnow()
        )
        db.add(registro)
        db.flush()

    # Registra saída quando a vaga é liberada
    elif novo_status == StatusVaga.LIVRE and status_anterior == StatusVaga.OCUPADA:
        ultimo_registro = db.query(Historico).filter(
            Historico.vaga_id == vaga.id,
            Historico.saida_em.is_(None)
        ).order_by(Historico.entrada_em.desc()).first()

        if ultimo_registro:
            ultimo_registro.saida_em = datetime.utcnow()
            tempo_perm = int((ultimo_registro.saida_em - ultimo_registro.entrada_em).total_seconds() / 60)
            ultimo_registro.tempo_permanencia_minutos = tempo_perm

    vaga.status = novo_status
    vaga.ultima_atualizacao = datetime.utcnow()

    db.commit()
    db.refresh(vaga)

    # Adiciona numero do andar na resposta
    if andar:
        vaga.numero_andar = andar.numero_andar

    return vaga
