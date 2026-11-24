
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models.db_models import Andar, Estacionamento, StatusVaga, TipoVaga, Usuario, Vaga
from models.schemas import AndarCreate, EstacionamentoCreate
from rules.elegibilidade_service import credencial_valida


def _contabilizar_vagas(db: Session, est: Estacionamento) -> None:
    """Vitrine e detalhe usam EXATAMENTE a mesma regra por andar.

    Livres = somente status livre. Ocupadas = ocupada + reservada.
    Inativas nao contam como disponiveis nem como ocupadas. Nao grava
    nenhum valor no banco: os atributos calculados sao serializados na API.
    """
    linhas = (
        db.query(
            Vaga.andar_id,
            func.count(Vaga.id),
            func.sum(case((Vaga.status == StatusVaga.LIVRE, 1), else_=0)),
            func.sum(case((
                Vaga.status.in_([StatusVaga.OCUPADA, StatusVaga.RESERVADA]), 1
            ), else_=0)),
        )
        .join(Andar, Andar.id == Vaga.andar_id)
        .filter(Andar.estacionamento_id == est.id)
        .group_by(Vaga.andar_id)
        .all()
    )
    por_andar = {
        andar_id: (int(total or 0), int(livres or 0), int(ocupadas or 0))
        for andar_id, total, livres, ocupadas in linhas
    }
    est.total_vagas = 0
    est.vagas_disponiveis_total = 0
    for andar in est.andares:
        total, livres, ocupadas = por_andar.get(andar.id, (0, 0, 0))
        andar.vagas_livres = livres
        andar.vagas_ocupadas = ocupadas
        est.total_vagas += total
        est.vagas_disponiveis_total += livres


def listar_todos_estacionamentos(
    db: Session, apenas_ids: list[str] | set[str] | None = None
) -> list[Estacionamento]:
    """Vitrine pública: totais e andares sincronizados, com escopo RBAC."""
    query = db.query(Estacionamento)
    if apenas_ids is not None:
        query = query.filter(Estacionamento.id.in_(list(apenas_ids)))
    estacionamentos = query.order_by(Estacionamento.nome).all()
    for est in estacionamentos:
        _contabilizar_vagas(db, est)
    return estacionamentos


def buscar_estacionamento_por_id(db: Session, estacionamento_id: str) -> Estacionamento | None:
    """Consulta de detalhe com a mesma contabilização da vitrine."""
    est = db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).first()
    if est is not None:
        _contabilizar_vagas(db, est)
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
    Motor da V1: sugere vaga especial apenas para credenciais oficiais
    verificadas e vigentes. Um booleano legado is_pcd ou uma idade declarada
    não substituem a autorização. Para usuários comuns prioriza vaga comum.
    """
    eh_pcd = bool(usuario and credencial_valida(db, usuario.id, "pcd"))
    eh_idoso = bool(usuario and credencial_valida(db, usuario.id, "idoso"))
    query = db.query(Vaga).join(Andar).filter(
        Andar.estacionamento_id == estacionamento_id,
        Vaga.status == StatusVaga.LIVRE
    )
    aviso = None

    if not eh_pcd:
        query = query.filter(Vaga.tipo != TipoVaga.PCD.value)
    if not eh_idoso:
        query = query.filter(Vaga.tipo != TipoVaga.IDOSO.value)
    if tipo_vaga_desejado == "normal":
        tipo_vaga_desejado = TipoVaga.COMUM.value

    if tipo_vaga_desejado in {"pcd", "idoso"} and (
        (tipo_vaga_desejado == "pcd" and not eh_pcd)
        or (tipo_vaga_desejado == "idoso" and not eh_idoso)
    ):
        aviso = "Vagas reservadas a idoso/PCD exigem credencial oficial validada. Exibimos opções comuns."
        tipo_vaga_desejado = TipoVaga.COMUM.value

    vaga = None
    if tipo_vaga_desejado:
        vaga = query.filter(Vaga.tipo == tipo_vaga_desejado).first()
    elif eh_pcd:
        vaga = query.filter(Vaga.tipo == TipoVaga.PCD.value).first()
    elif eh_idoso:
        vaga = query.filter(Vaga.tipo == TipoVaga.IDOSO.value).first()
    else:
        vaga = query.filter(Vaga.tipo == TipoVaga.COMUM.value).first()

    if not vaga:
        vaga = query.first()

    if not vaga:
        return None, None, aviso

    andar = db.query(Andar).filter(Andar.id == vaga.andar_id).first()
    return vaga, andar.numero_andar if andar else None, aviso
