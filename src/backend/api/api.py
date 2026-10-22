import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.config import settings
from core.rate_limiter import limiter, LIMITS
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
@limiter.limit(LIMITS["criar_reserva"])
async def criar_reserva(
    request: Request,
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
@limiter.limit(LIMITS["atualiza_status_vaga"])
async def atualizar_status_vaga(
    request: Request,
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
@limiter.limit(LIMITS["relatorios"])
async def relatorio_fluxo(
    request: Request,
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
@limiter.limit(LIMITS["relatorios"])
async def relatorio_ocupacao(
    request: Request,
    periodo: str = Query(..., description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro),
):
    """Taxa de ocupação histórica e dados para mapas de calor por andar (painel)"""
    return relatorio_service.gerar_relatorio_ocupacao(
        db, periodo, garantir_escopo_relatorio(usuario, estacionamento_id)
    )


# ======================================================================
# MARCA 3 · RF-51/52/54/55 — ocupação histórica, rotação e exportações CSV
# (tudo escopado por papel com o MESMO garantidor dos demais relatórios)
# ======================================================================

def _csv_response(nome: str, linhas: list[list]) -> StreamingResponse:
    """text/csv com BOM (Excel pt-BR abre sem gambiarra de encoding)."""
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    for ln in linhas:
        w.writerow(ln)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}_{stamp}.csv"'},
    )


@router.get("/relatorios/ocupacao-historica")
@limiter.limit(LIMITS["relatorios"])
async def relatorio_ocupacao_historica(
    request: Request,
    periodo: str = Query("semanal", description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro),
):
    """
    RF-52 (ADR-09): matriz hora × andar DERIVADA dos intervalos do Histórico —
    ocupação média por hora do dia LOCAL (America/Manaus) na janela pedida.
    """
    return relatorio_service.gerar_relatorio_ocupacao_historica(
        db, periodo, garantir_escopo_relatorio(usuario, estacionamento_id)
    )


@router.get("/relatorios/rotacao")
@limiter.limit(LIMITS["relatorios"])
async def relatorio_rotacao(
    request: Request,
    periodo: str = Query("diario", description="Período: diario, semanal, mensal"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro),
):
    """RF-54: giro (entradas ÷ vagas ativas) e tempo médio por andar no período."""
    return relatorio_service.gerar_relatorio_rotacao(
        db, periodo, garantir_escopo_relatorio(usuario, estacionamento_id)
    )


@router.get("/relatorios/fluxo/csv")
@limiter.limit(LIMITS["relatorios"])
async def relatorio_fluxo_csv(
    request: Request,
    periodo: str = Query("diario"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro),
):
    """RF-55: uma linha por estadia (placa, entrada, saída, minutos, valor)."""
    dados = relatorio_service.gerar_relatorio_fluxo(
        db, periodo, garantir_escopo_relatorio(usuario, estacionamento_id)
    )
    linhas = [["id", "entrada_em", "saida_em", "placa", "tempo_min", "valor_total"]]
    for r in dados["registros"]:
        linhas.append([
            r["id"],
            r["entrada_em"].isoformat(sep=" ", timespec="minutes") if r["entrada_em"] else "",
            r["saida_em"].isoformat(sep=" ", timespec="minutes") if r["saida_em"] else "",
            r["placa"] or "",
            r["tempo_permanencia"] if r["tempo_permanencia"] is not None else "",
            f'{r["valor_total"]:.2f}' if r["valor_total"] is not None else "",
        ])
    return _csv_response("fluxo", linhas)


@router.get("/relatorios/financeiro/csv")
@limiter.limit(LIMITS["relatorios"])
async def relatorio_financeiro_csv(
    request: Request,
    periodo: str = Query("diario"),
    estacionamento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro),
):
    """RF-55: pagamentos do período (método/status/valores), escopo por papel."""
    from models.db_models import Pagamento
    from rules import financeiro_service

    est = garantir_escopo_relatorio(usuario, estacionamento_id)
    ini, fim = financeiro_service._calcular_periodo(periodo)
    q = db.query(Pagamento).filter(
        Pagamento.data_pagamento >= ini, Pagamento.data_pagamento < fim
    )
    if est:
        q = q.filter(Pagamento.estacionamento_id == est)
    linhas = [["id", "data", "metodo", "status", "valor_bruto", "desconto", "valor_total"]]
    for p in q.order_by(Pagamento.data_pagamento.desc()).all():
        linhas.append([
            p.id,
            p.data_pagamento.strftime("%Y-%m-%d %H:%M") if p.data_pagamento else "",
            p.metodo_pagamento, p.status_pagamento,
            f"{p.valor_bruto or 0:.2f}", f"{p.valor_desconto or 0:.2f}", f"{p.valor_total or 0:.2f}",
        ])
    return _csv_response("financeiro", linhas)
