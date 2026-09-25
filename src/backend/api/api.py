from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.config import settings
from core.deps import get_usuario_logado
from models.database import get_db
from models.db_models import Usuario
from models.schemas import (
    EstacionamentoDetalhadoResponse,
    VagaResponse,
    MapaVagasResponse,
    ProximaVagaResponse,
    ReservaCreate,
    ReservaResponse,
    FluxoResponse,
    OcupacaoResponse,
    StatusResponse,
    HealthCheckResponse,
    VagaAtualizaStatus,
)
from rules import (
    estacionamento_service,
    vaga_service,
    reserva_service,
    relatorio_service,
)

router = APIRouter(prefix=settings.API_V2_PREFIX, tags=["SmartParking"])


# --- Rotas de status e saúde ---
@router.get("/", response_model=StatusResponse)
async def status_api():
    """Status geral da API"""
    return {
        "status": "SmartParking API está rodando perfeitamente!",
        "versao": settings.APP_VERSION,
        "ambiente": settings.ENVIRONMENT,
        "docs": "/docs",
    }


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """Verificação de saúde: testa conexão com banco de dados"""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "saudavel" if db_ok else "banco_indisponivel",
        "banco_dados": db_ok,
    }


@router.get("/version")
async def version():
    """Retorna a versão atual da API"""
    return {"version": settings.APP_VERSION}


@router.get("/status")
async def status():
    """Endpoint de status compatível com o seu código original"""
    return {"status": "SmartParking API está rodando perfeitamente!"}


# --- Rotas de Estacionamentos ---
@router.get("/estacionamentos", response_model=list[EstacionamentoDetalhadoResponse])
async def listar_estacionamentos(db: Session = Depends(get_db)):
    """Lista todos os estacionamentos com contagem de vagas por andar"""
    return estacionamento_service.listar_todos_estacionamentos(db)


@router.get("/estacionamentos/{id}/vagas", response_model=MapaVagasResponse)
async def mapa_vagas(id: str, db: Session = Depends(get_db)):
    """
    Retorna o mapa completo de vagas detalhado de um estacionamento específico,
    organizado por andares
    """
    estacionamento = estacionamento_service.buscar_estacionamento_por_id(db, id)
    if not estacionamento:
        raise HTTPException(status_code=404, detail="Estacionamento não encontrado")

    andares, vagas = estacionamento_service.listar_vagas_estacionamento(db, id)

    return {
        "estacionamento_id": id,
        "estacionamento_nome": estacionamento.nome,
        "andares": andares,
        "vagas": vagas,
    }


@router.get("/estacionamentos/{id}/proxima-vaga", response_model=ProximaVagaResponse)
async def proxima_vaga(
    id: str,
    tipo_vaga: Optional[str] = Query(
        None, description="Tipo de vaga: comum, idoso, pcd, moto, eletrico"
    ),
    db: Session = Depends(get_db),
):
    """Consulta o motor de atribuição para obter a próxima vaga disponível"""
    estacionamento = estacionamento_service.buscar_estacionamento_por_id(db, id)
    if not estacionamento:
        raise HTTPException(status_code=404, detail="Estacionamento não encontrado")

    vaga, andar_numero = estacionamento_service.buscar_proxima_vaga_disponivel(
        db, id, tipo_vaga
    )

    return {
        "estacionamento_id": id,
        "vaga": vaga,
        "andar_numero": andar_numero,
        "mensagem": (
            f"Vaga encontrada no {andar_numero}º andar!"
            if vaga
            else "Não há vagas disponíveis no momento."
        ),
    }


# --- Rotas de Reservas (requerem autenticação) ---
@router.post("/reservas", response_model=ReservaResponse, status_code=201)
async def criar_reserva(
    dados: ReservaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """Cria uma nova reserva vinculada ao usuário logado"""
    return reserva_service.criar_reserva(db, dados, usuario)


@router.delete("/reservas/{id}", response_model=ReservaResponse)
async def cancelar_reserva(
    id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """Cancela uma reserva e libera a vaga imediatamente"""
    return reserva_service.cancelar_reserva(db, id, usuario)


@router.get("/reservas/minhas", response_model=list[ReservaResponse])
async def listar_minhas_reservas(
    db: Session = Depends(get_db), usuario: Usuario = Depends(get_usuario_logado)
):
    """Lista todas as reservas do usuário logado"""
    return reserva_service.listar_reservas_usuario(db, usuario.id)


# --- Rotas de Vagas ---
@router.patch("/vagas/{id}/status", response_model=VagaResponse)
async def atualizar_status_vaga(
    id: str, dados: VagaAtualizaStatus, db: Session = Depends(get_db)
):
    """
    Atualiza o status de uma vaga (uso manual ou integração com sensores).
    Status aceitos: livre, ocupada, reservada, inativa
    """
    return vaga_service.atualizar_status_vaga(db, id, dados)


# --- Rotas de Relatórios ---
@router.get("/relatorios/fluxo", response_model=FluxoResponse)
async def relatorio_fluxo(
    periodo: str = Query(..., description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Relatórios de entradas e saídas por período"""
    return relatorio_service.gerar_relatorio_fluxo(db, periodo, estacionamento_id)


@router.get("/relatorios/ocupacao", response_model=OcupacaoResponse)
async def relatorio_ocupacao(
    periodo: str = Query(..., description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Taxa de ocupação histórica e dados para mapas de calor por andar"""
    return relatorio_service.gerar_relatorio_ocupacao(db, periodo, estacionamento_id)
