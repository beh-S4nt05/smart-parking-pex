from typing import List, Optional

from sqlalchemy.orm import Session

from models.db_models import Estacionamento, Andar, Vaga, StatusVaga
from models.schemas import EstacionamentoCreate, AndarCreate


def listar_todos_estacionamentos(db: Session) -> List[Estacionamento]:
    """Retorna todos os estacionamentos com contagem de vagas disponíveis"""
    estacionamentos = db.query(Estacionamento).all()

    for est in estacionamentos:
        total_vagas = db.query(Vaga).join(Andar).filter(
            Andar.estacionamento_id == est.id
        ).count()
        vagas_ocupadas = db.query(Vaga).join(Andar).filter(
            Andar.estacionamento_id == est.id,
            Vaga.status.in_([StatusVaga.OCUPADA, StatusVaga.RESERVADA])
        ).count()
        est.total_vagas = total_vagas
        est.vagas_disponiveis_total = total_vagas - vagas_ocupadas

    return estacionamentos


def buscar_estacionamento_por_id(db: Session, estacionamento_id: str) -> Optional[Estacionamento]:
    """Busca um estacionamento pelo ID (UUID)"""
    est = db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).first()
    if est:
        # Adiciona contagem de vagas por andar
        for andar in est.andares:
            total_vagas_andar = db.query(Vaga).filter(Vaga.andar_id == andar.id).count()
            vagas_ocupadas = db.query(Vaga).filter(
                Vaga.andar_id == andar.id,
                Vaga.status.in_([StatusVaga.OCUPADA, StatusVaga.RESERVADA])
            ).count()
            andar.vagas_ocupadas = vagas_ocupadas
            andar.vagas_livres = total_vagas_andar - vagas_ocupadas

        total_vagas = sum(db.query(Vaga).filter(Vaga.andar_id == a.id).count() for a in est.andares)
        vagas_ocupadas_total = sum(
            db.query(Vaga).filter(
                Vaga.andar_id == a.id,
                Vaga.status.in_([StatusVaga.OCUPADA, StatusVaga.RESERVADA])
            ).count() for a in est.andares
        )
        est.vagas_disponiveis_total = total_vagas - vagas_ocupadas_total

    return est


def criar_estacionamento(db: Session, dados: EstacionamentoCreate) -> Estacionamento:
    """Cria um novo estacionamento"""
    novo_est = Estacionamento(**dados.model_dump())
    db.add(novo_est)
    db.commit()
    db.refresh(novo_est)
    return novo_est


def criar_andar(db: Session, dados: AndarCreate) -> Andar:
    """Adiciona um novo andar a um estacionamento"""
    novo_andar = Andar(**dados.model_dump())
    db.add(novo_andar)
    db.commit()
    db.refresh(novo_andar)
    return novo_andar


def listar_vagas_estacionamento(db: Session, estacionamento_id: str):
    """Retorna todos os andares e vagas de um estacionamento para o mapa"""
    andares = db.query(Andar).filter(Andar.estacionamento_id == estacionamento_id).all()
    vagas = db.query(Vaga).join(Andar).filter(
        Andar.estacionamento_id == estacionamento_id
    ).all()

    # Adiciona numero do andar em cada vaga
    for vaga in vagas:
        andar = next((a for a in andares if a.id == vaga.andar_id), None)
        vaga.numero_andar = andar.numero_andar if andar else None

    return andares, vagas


def buscar_proxima_vaga_disponivel(
    db: Session,
    estacionamento_id: str,
    tipo_vaga_desejado: Optional[str] = None
) -> tuple[Optional[Vaga], Optional[int]]:
    """
    Motor de atribuição de próxima vaga:
    Busca a primeira vaga livre, priorizando o tipo desejado,
    retornando também o número do andar da vaga.
    """
    query = db.query(Vaga).join(Andar).filter(
        Andar.estacionamento_id == estacionamento_id,
        Vaga.status == StatusVaga.LIVRE
    )

    vaga = None
    if tipo_vaga_desejado:
        vaga = query.filter(Vaga.tipo == tipo_vaga_desejado).first()

    if not vaga:
        vaga = query.first()

    if not vaga:
        return None, None

    andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
    return vaga, andar.numero_andar if andar else None
