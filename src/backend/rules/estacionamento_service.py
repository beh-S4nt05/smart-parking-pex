
from sqlalchemy.orm import Session

from models.db_models import Andar, Estacionamento, StatusVaga, TipoVaga, Usuario, Vaga
from models.schemas import AndarCreate, EstacionamentoCreate


def listar_todos_estacionamentos(db: Session) -> list[Estacionamento]:
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


def buscar_estacionamento_por_id(db: Session, estacionamento_id: str) -> Estacionamento | None:
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
    tipo_vaga_desejado: str | None = None,
    usuario: Usuario | None = None,
) -> tuple[Vaga | None, int | None, str | None]:
    """
    Motor de atribuição de próxima vaga (RF-47):
    Busca a primeira vaga livre, priorizando o tipo desejado, retornando
    também o andar e um AVISO quando a elegibilidade PCD mexeu no resultado.

    Regra da vaga PCD (medida do relato do usuário em 22/10-rod.5): a vaga
    PCD só é atribuída a motorista com `is_pcd` declarado no cadastro/perfil.
    Anônimo ou não-declarado = motorista COMUM — recebe "vaga normal", nunca
    PCD, mesmo que a PCD seja a mais próxima. Para o declarado PCD, a PCD é
    PRIORITÁRIA (cai para comum se não houver livre).
    """
    eh_pcd = bool(usuario and usuario.is_pcd)
    query = db.query(Vaga).join(Andar).filter(
        Andar.estacionamento_id == estacionamento_id,
        Vaga.status == StatusVaga.LIVRE
    )
    aviso = None

    if not eh_pcd:
        query = query.filter(Vaga.tipo != TipoVaga.PCD.value)
        if tipo_vaga_desejado == TipoVaga.PCD.value:
            tipo_vaga_desejado = None
            aviso = (
                "Vagas PCD são reservadas a motoristas com deficiência "
                "declarada no cadastro. Atribuímos uma vaga comum."
            )
        elif tipo_vaga_desejado == "normal":
            # sinônimo histórico do Figma → vocabulário oficial do sistema
            tipo_vaga_desejado = TipoVaga.COMUM.value

    vaga = None
    if tipo_vaga_desejado:
        vaga = query.filter(Vaga.tipo == tipo_vaga_desejado).first()
    elif eh_pcd:
        # PCD declarado: prioriza a vaga especial livre
        vaga = query.filter(Vaga.tipo == TipoVaga.PCD.value).first()

    if not vaga:
        vaga = query.first()

    if not vaga:
        return None, None, aviso

    andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
    return vaga, andar.numero_andar if andar else None, aviso
