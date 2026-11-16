
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.timeutils import utc_agora
from models.db_models import Andar, Reserva, StatusReserva, StatusVaga, TipoVaga, Usuario, Vaga, Veiculo
from models.schemas import ReservaCreate
from rules.elegibilidade_service import credencial_valida


def expirar_reservas_vencidas(db: Session) -> int:
    """
    RF-23 (marca 3 · ACH-10): reservas CONFIRMADA com horário de fim no
    passado viram EXPIRADA e a vaga é liberada (se ainda estiver presa a
    ela). Idempotente — chamado nas leituras do app/painel e pelo loop de
    fundo do `main.py` (60 s). Retorna quantas expiraram.
    """
    agora = utc_agora()
    vencidas = db.query(Reserva).filter(
        Reserva.status == StatusReserva.CONFIRMADA,
        Reserva.horario_fim < agora,
    ).all()

    for reserva in vencidas:
        reserva.status = StatusReserva.EXPIRADA
        vaga = db.query(Vaga).filter(Vaga.id == reserva.vaga_id).first()
        if vaga and vaga.status == StatusVaga.RESERVADA:
            vaga.status = StatusVaga.LIVRE
            vaga.ultima_atualizacao = agora

    if vencidas:
        db.commit()
    return len(vencidas)


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

    # O veículo é sempre identificado no escopo do usuário autenticado.
    veiculo = None
    if dados.veiculo_id:
        veiculo = db.query(Veiculo).filter(
            Veiculo.id == dados.veiculo_id,
            Veiculo.usuario_id == usuario_logado.id,
            Veiculo.ativo.is_(True),
        ).first()
        if not veiculo:
            raise HTTPException(status_code=403, detail="Veículo não pertence à sua conta")

    # Conta com garagem não pode ignorar a seleção para escapar dos
    # critérios de compatibilidade. Conta legada sem veículos mantém a
    # possibilidade de reservar vaga comum sem veículo.
    if not dados.veiculo_id and db.query(Veiculo.id).filter(
        Veiculo.usuario_id == usuario_logado.id,
        Veiculo.ativo.is_(True),
    ).first() is not None:
        raise HTTPException(
            status_code=422,
            detail="Selecione um dos veículos cadastrados para esta reserva.",
        )

    # Vaga especial: documento oficial verificado, não a autodeclaração.
    credencial = None
    if vaga.tipo in {TipoVaga.PCD.value, TipoVaga.IDOSO.value}:
        credencial = credencial_valida(db, usuario_logado.id, vaga.tipo)
        if not credencial:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vaga exclusiva para beneficiário com credencial oficial validada. Solicite a verificação em Minha conta.",
            )

    # Sem veículo informado ainda é permitido reservar vaga comum legado.
    # Para moto/recarga ou categoria explicitamente restrita, não é possível
    # decidir compatibilidade sem um veículo cadastrado e selecionado.
    if (vaga.tipo in {TipoVaga.MOTO.value, TipoVaga.ELETRICO.value}
        or vaga.categoria_veiculo is not None or vaga.recarga_disponivel) and not veiculo:
        raise HTTPException(
            status_code=422,
            detail="Selecione um veículo cadastrado para confirmar esta vaga.",
        )
    if veiculo:
        categoria = vaga.categoria_veiculo
        if categoria in {"carro", "moto"} and veiculo.categoria != categoria:
            raise HTTPException(status_code=422, detail="Seu veículo não é compatível com o tipo desta vaga.")
        if vaga.tipo == TipoVaga.MOTO.value and veiculo.categoria != "moto":
            raise HTTPException(status_code=422, detail="Vaga reservada para motocicletas.")
        if vaga.tipo == TipoVaga.ELETRICO.value:
            if veiculo.motorizacao != "eletrico":
                raise HTTPException(status_code=422, detail="Vaga de recarga reservada para veículo elétrico.")
            if categoria is None and veiculo.categoria != "carro":
                raise HTTPException(status_code=422, detail="Esta vaga elétrica é para carros; motos elétricas exigem vaga compatível.")
        if vaga.recarga_disponivel and veiculo.motorizacao != "eletrico":
            raise HTTPException(status_code=422, detail="Vaga de recarga requer veículo elétrico compatível.")
        if vaga.conector_tipo and veiculo.conector_tipo != vaga.conector_tipo:
            raise HTTPException(status_code=422, detail="Conector de recarga incompatível.")

    if dados.horario_fim <= dados.horario_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Horário de fim deve ser posterior ao horário de início"
        )

    # Cria a reserva
    nova_reserva = Reserva(
        **dados.model_dump(),
        credencial_id=credencial.id if credencial else None,
        usuario_id=usuario_logado.id,
        status=StatusReserva.CONFIRMADA
    )

    # Atualiza status da vaga
    vaga.status = StatusVaga.RESERVADA
    vaga.ultima_atualizacao = utc_agora()

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

    if reserva.status != StatusReserva.CONFIRMADA:
        detalhe = (
            "Reserva já está cancelada"
            if reserva.status == StatusReserva.CANCELADA
            else "Somente uma reserva confirmada pode ser cancelada"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detalhe)

    # Atualiza status da reserva
    reserva.status = StatusReserva.CANCELADA

    # Libera a vaga se ela ainda estava reservada
    vaga = db.query(Vaga).filter(Vaga.id == reserva.vaga_id).first()
    if vaga and vaga.status == StatusVaga.RESERVADA:
        vaga.status = StatusVaga.LIVRE
        vaga.ultima_atualizacao = utc_agora()

    db.commit()
    db.refresh(reserva)

    # Adiciona dados da vaga
    if vaga:
        andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
        if andar:
            vaga.numero_andar = andar.numero_andar
        reserva.vaga = vaga

    return reserva


def listar_reservas_usuario(db: Session, usuario_id: str) -> list[Reserva]:
    """Lista todas as reservas de um usuário específico (expira as vencidas antes)."""
    expirar_reservas_vencidas(db)
    reservas = db.query(Reserva).filter(Reserva.usuario_id == usuario_id).all()

    # Adiciona dados do andar em cada vaga
    for reserva in reservas:
        if reserva.vaga:
            andar = db.query(Andar).filter(Andar.id == reserva.vaga.andar_id).first()
            if andar:
                reserva.vaga.numero_andar = andar.numero_andar

    return reservas
