from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.config import settings
from core.deps import (
    get_usuario_financeiro,
    get_usuario_gestor,
    get_usuario_logado,
)
from models.database import get_db
from models.db_models import Andar, TipoUsuario, Usuario, Vaga
from models.schemas import (
    EstacionamentoDetalhadoResponse,
    VagaResponse,
    MapaVagasResponse,
    ProximaVagaResponse,
    ReservaCreate,
    ReservaResponse,
    FluxoResponse,
    FluxoPublicoResponse,
    OcupacaoResponse,
    StatusResponse,
    HealthCheckResponse,
    VagaAtualizaStatus,
    VagaLoteStatusUpdate,
    VagaLoteResponse,
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
@router.get("/vagas", response_model=list[VagaResponse])
async def listar_vagas(
    estacionamento_id: Optional[str] = Query(None, description="Filtra por estacionamento"),
    andar_id: Optional[str] = Query(None, description="Filtra por andar"),
    status: Optional[str] = Query(None, description="livre, ocupada, reservada ou inativa"),
    tipo: Optional[str] = Query(None, description="comum, idoso, pcd, moto ou eletrico"),
    db: Session = Depends(get_db),
):
    """Lista vagas com filtros opcionais (consulta rápida para o mapa do app)"""
    return vaga_service.listar_vagas(db, estacionamento_id, andar_id, status, tipo)


# --- Controle de acesso das rotas de escrita/leitura sensíveis (auditoria 20/10) ---
# Antes dessas proteções, QUALQUER pessoa na rede conseguia mudar o status de
# vagas (PATCH /api/vagas/*/status público) e ler o relatório financeiro
# detalhado (GET /api/relatorios/fluxo trazia registros com valor_total).


def garantir_vagas_no_escopo(db: Session, usuario: Usuario, vaga_ids: list[str]) -> None:
    """
    Admin opera em qualquer vaga do sistema. Gestor só pode alterar status de
    vagas do estacionamento ao qual está vinculado (vaga -> andar ->
    estacionamento) — nada de "retornar vazio" que parece bug: 403 na cara.
    """
    if usuario.role == TipoUsuario.ADMIN.value:
        return
    fora_do_escopo = (
        db.query(Vaga.id)
        .join(Andar, Vaga.andar_id == Andar.id)
        .filter(Vaga.id.in_(vaga_ids), Andar.estacionamento_id != usuario.estacionamento_id)
        .count()
    )
    if fora_do_escopo:
        raise HTTPException(
            status_code=403,
            detail="Uma ou mais vagas não pertencem ao seu estacionamento.",
        )


def garantir_escopo_relatorio(
    usuario: Usuario, estacionamento_id: Optional[str]
) -> Optional[str]:
    """
    Admin vê o todo (ou o estacionamento que filtrar). Gestor/financeiro:
    forçado ao próprio estacionamento; pedir o dos outros é 403, não dados
    vazios que confundem na demo.
    """
    if usuario.role == TipoUsuario.ADMIN.value:
        return estacionamento_id
    if estacionamento_id and estacionamento_id != usuario.estacionamento_id:
        raise HTTPException(
            status_code=403,
            detail="Você só pode visualizar relatórios do seu estacionamento.",
        )
    return usuario.estacionamento_id


# ATENÇÃO: a rota fixa /vagas/lote/status precisa ser declarada ANTES da
# dinâmica /vagas/{id}/status — senão o FastAPI casa "lote" como {id} (404)
@router.patch("/vagas/lote/status", response_model=VagaLoteResponse)
async def atualizar_status_vagas_lote(
    dados: VagaLoteStatusUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_gestor),
):
    """
    Atualiza o status de várias vagas de uma vez — usado pelas ações do
    simulador de sensores (ex.: "ocupar 10 livres", "liberar andar inteiro").
    Requer admin/gestor (o fluxo do app sempre manda o Bearer token); gestor
    limitado às vagas do próprio estacionamento.
    Mantém o histórico de entrada/saída para cada transição válida.
    """
    garantir_vagas_no_escopo(db, usuario, dados.vaga_ids)
    return vaga_service.atualizar_status_vaga_lote(db, dados)


@router.patch("/vagas/{id}/status", response_model=VagaResponse)
async def atualizar_status_vaga(
    id: str,
    dados: VagaAtualizaStatus,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_gestor),
):
    """
    Atualiza o status de uma vaga (uso manual do painel ou integração com
    sensores). Requer admin/gestor; gestor só no próprio estacionamento.
    Status aceitos: livre, ocupada, reservada, inativa
    """
    garantir_vagas_no_escopo(db, usuario, [id])
    return vaga_service.atualizar_status_vaga(db, id, dados)


# --- Rotas de Relatórios ---
# O fluxo DETALHADO (registros com valores) virou rota de painel:
# admin/financeiro/gestor, cada um no seu escopo. Para telas públicas (Home)
# existe /relatorios/fluxo/publico só com agregados — foi essa a fonte que o
# StatusPanel da Home sempre usou (tempo_medio_permanencia_min).
@router.get("/relatorios/fluxo", response_model=FluxoResponse)
async def relatorio_fluxo(
    periodo: str = Query(..., description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro),
):
    """Relatórios de entradas e saídas por período (painel; com registros)"""
    return relatorio_service.gerar_relatorio_fluxo(
        db, periodo, garantir_escopo_relatorio(usuario, estacionamento_id)
    )


@router.get("/relatorios/fluxo/publico", response_model=FluxoPublicoResponse)
async def relatorio_fluxo_publico(
    periodo: str = Query("diario", description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Agregados seguros (entradas/saídas/tempo médio) para a Home pública.
    NÃO expõe `registros`: nem placa, nem valor — nada de cliente alheio.
    """
    dados = relatorio_service.gerar_relatorio_fluxo(db, periodo, estacionamento_id)
    return {
        chave: dados[chave]
        for chave in (
            "periodo",
            "estacionamento_id",
            "total_entradas",
            "total_saidas",
            "tempo_medio_permanencia_min",
        )
    }


@router.get("/relatorios/ocupacao", response_model=OcupacaoResponse)
async def relatorio_ocupacao(
    periodo: str = Query(..., description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro),
):
    """Taxa de ocupação histórica e dados para mapas de calor por andar (painel)"""
    return relatorio_service.gerar_relatorio_ocupacao(
        db, periodo, garantir_escopo_relatorio(usuario, estacionamento_id)
    )
