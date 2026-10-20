from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.db_models import Vaga, StatusVaga, Historico, Andar
from models.schemas import VagaCreate, VagaAtualizaStatus, VagaLoteStatusUpdate


def buscar_vaga_por_id(db: Session, vaga_id: str) -> Optional[Vaga]:
    """Busca uma vaga pelo ID UUID"""
    return db.query(Vaga).filter(Vaga.id == vaga_id).first()


def listar_vagas(
    db: Session,
    estacionamento_id: Optional[str] = None,
    andar_id: Optional[str] = None,
    status_vaga: Optional[str] = None,
    tipo: Optional[str] = None,
) -> List[Vaga]:
    """
    Lista vagas com filtros opcionais (shopping, andar, status e tipo),
    já anotando o número do andar em cada vaga para o mapa do app.
    """
    query = db.query(Vaga).join(Andar, Vaga.andar_id == Andar.id)

    if estacionamento_id:
        query = query.filter(Andar.estacionamento_id == estacionamento_id)
    if andar_id:
        query = query.filter(Vaga.andar_id == andar_id)
    if status_vaga:
        query = query.filter(Vaga.status == status_vaga)
    if tipo:
        query = query.filter(Vaga.tipo == tipo)

    vagas = query.order_by(Andar.numero_andar, Vaga.codigo).all()

    for vaga in vagas:
        if vaga.andar:
            vaga.numero_andar = vaga.andar.numero_andar
    return vagas


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


def _registrar_transicao(
    db: Session, vaga: Vaga, novo_status: str, origem: Optional[str] = None
) -> None:
    """
    Aplica o novo status na vaga e mantém o histórico de entrada/saída
    consistente. NÃO faz commit — quem chama decide quando persistir
    (isso permite a versão em lote committing apenas uma vez).
    """
    status_anterior = vaga.status

    if status_anterior == novo_status:
        return

    andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
    estacionamento_id = andar.estacionamento_id if andar else None

    # Registra entrada quando a vaga passa a ser ocupada
    if novo_status == StatusVaga.OCUPADA and status_anterior == StatusVaga.LIVRE:
        registro = Historico(
            estacionamento_id=estacionamento_id,
            vaga_id=vaga.id,
            entrada_em=datetime.now(),
            origem=origem or "sensor",
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
            ultimo_registro.saida_em = datetime.now()
            tempo_perm = int(
                (ultimo_registro.saida_em - ultimo_registro.entrada_em).total_seconds() / 60
            )
            ultimo_registro.tempo_permanencia_minutos = tempo_perm

    vaga.status = novo_status
    vaga.ultima_atualizacao = datetime.now()


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

    _registrar_transicao(db, vaga, dados.status, getattr(dados, "origem", None))

    db.commit()
    db.refresh(vaga)

    # Adiciona numero do andar na resposta
    if vaga.andar:
        vaga.numero_andar = vaga.andar.numero_andar

    return vaga


def atualizar_status_vaga_lote(
    db: Session,
    dados: VagaLoteStatusUpdate
) -> dict:
    """
    Atualiza o status de várias vagas de uma vez (simulador de sensores).

    - IDs inexistentes são ignorados e reportados em `nao_encontradas`
    - O histórico de entrada/saída é mantido para cada transição válida
    - Um único commit ao final (operação atômica para o simulador)
    """
    ids_unicos = list(dict.fromkeys(dados.vaga_ids))  # remove duplicados preservando ordem
    vagas = (
        db.query(Vaga)
        .filter(Vaga.id.in_(ids_unicos))
        .options()
        .all()
    )
    encontradas = {vaga.id for vaga in vagas}
    nao_encontradas = [v for v in ids_unicos if v not in encontradas]

    atualizadas = 0
    for vaga in vagas:
        antes = vaga.status
        _registrar_transicao(db, vaga, dados.status, getattr(dados, "origem", None))
        if antes != vaga.status:
            atualizadas += 1

    db.commit()

    for vaga in vagas:
        if vaga.andar:
            vaga.numero_andar = vaga.andar.numero_andar

    return {
        "solicitadas": len(ids_unicos),
        "atualizadas": atualizadas,
        "nao_encontradas": nao_encontradas,
        "vagas": vagas,
    }
