from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from models.db_models import (
    Pagamento, Historico, ConfiguracaoPreco, Estacionamento,
    Vaga, TipoVaga, TipoUsuario
)
from models.schemas import (
    ConfiguracaoPrecoCreate, RegistrarPagamentoRequest
)


def _calcular_periodo(periodo: str) -> tuple[datetime, datetime]:
    """Calcula data de início e fim baseado no período solicitado"""
    hoje = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    if periodo == "diario":
        return hoje, hoje + timedelta(days=1)
    elif periodo == "semanal":
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        return inicio_semana, inicio_semana + timedelta(days=7)
    elif periodo == "mensal":
        inicio_mes = hoje.replace(day=1)
        if inicio_mes.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        return inicio_mes, fim_mes
    else:
        raise HTTPException(
            status_code=400,
            detail="Período inválido. Use: diario, semanal ou mensal"
        )


# --- Configuração de Preços ---
def criar_configuracao_preco(db: Session, dados: ConfiguracaoPrecoCreate) -> ConfiguracaoPreco:
    """Cria ou atualiza o preço para um tipo de vaga em um estacionamento"""
    # Verifica se já existe preço para esse tipo de vaga
    preco_existente = db.query(ConfiguracaoPreco).filter(
        ConfiguracaoPreco.estacionamento_id == dados.estacionamento_id,
        ConfiguracaoPreco.tipo_vaga == dados.tipo_vaga
    ).first()

    if preco_existente:
        # Atualiza o preço existente
        preco_existente.valor_hora = dados.valor_hora
        preco_existente.valor_diaria = dados.valor_diaria
        preco_existente.tolerancia_minutos = dados.tolerancia_minutos
        db.commit()
        db.refresh(preco_existente)
        return preco_existente

    novo_preco = ConfiguracaoPreco(**dados.model_dump())
    db.add(novo_preco)
    db.commit()
    db.refresh(novo_preco)
    return novo_preco


def listar_precos_estacionamento(db: Session, estacionamento_id: str):
    """Retorna todos os preços configurados para um estacionamento"""
    return db.query(ConfiguracaoPreco).filter(
        ConfiguracaoPreco.estacionamento_id == estacionamento_id
    ).all()


# --- Pagamentos ---
def registrar_pagamento(db: Session, dados: RegistrarPagamentoRequest, usuario_logado) -> Pagamento:
    """Registra um pagamento de estadia"""
    historico = db.query(Historico).filter(Historico.id == dados.historico_id).first()
    if not historico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de estadia não encontrado"
        )

    # Se for financeiro/gestor, só permite registrar pagamento no seu estacionamento
    if usuario_logado.role in [TipoUsuario.FINANCEIRO.value, TipoUsuario.GESTOR.value]:
        if historico.estacionamento_id != usuario_logado.estacionamento_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para registrar pagamentos em outro estacionamento"
            )

    # Atualiza o valor total no histórico
    historico.valor_total = dados.valor_total

    novo_pagamento = Pagamento(
        historico_id=dados.historico_id,
        estacionamento_id=historico.estacionamento_id,
        usuario_id=historico.usuario_id,
        valor_total=dados.valor_total,
        metodo_pagamento=dados.metodo_pagamento,
        comprovante_url=dados.comprovante_url,
        observacoes=dados.observacoes,
        status_pagamento="pago"
    )

    db.add(novo_pagamento)
    db.commit()
    db.refresh(novo_pagamento)
    return novo_pagamento


def listar_pagamentos_estacionamento(
    db: Session,
    estacionamento_id: str,
    periodo: str = "diario"
):
    """Lista todos os pagamentos de um estacionamento no período"""
    data_inicio, data_fim = _calcular_periodo(periodo)

    return db.query(Pagamento).filter(
        Pagamento.estacionamento_id == estacionamento_id,
        Pagamento.data_pagamento >= data_inicio,
        Pagamento.data_pagamento < data_fim
    ).order_by(Pagamento.data_pagamento.desc()).all()


# --- Resumo Financeiro ---
def obter_resumo_financeiro(
    db: Session,
    periodo: str = "diario",
    estacionamento_id: Optional[str] = None,
    usuario_logado = None
) -> dict:
    """
    Retorna resumo de faturamento do período com:
    - Faturamento total
    - Ticket médio
    - Quantidade de pagamentos por método
    - Valor por método de pagamento
    - Faturamento por dia
    """
    data_inicio, data_fim = _calcular_periodo(periodo)

    # Se for gestor/financeiro, só pode ver o próprio estacionamento
    if usuario_logado.role in [TipoUsuario.FINANCEIRO.value, TipoUsuario.GESTOR.value]:
        estacionamento_id = usuario_logado.estacionamento_id

    query = db.query(Pagamento).filter(
        Pagamento.data_pagamento >= data_inicio,
        Pagamento.data_pagamento < data_fim,
        Pagamento.status_pagamento == "pago"
    )

    if estacionamento_id:
        query = query.filter(Pagamento.estacionamento_id == estacionamento_id)

    pagamentos = query.all()

    if not pagamentos:
        return {
            "periodo": periodo,
            "estacionamento_id": estacionamento_id,
            "estacionamento_nome": None,
            "faturamento_total": 0.0,
            "ticket_medio": 0.0,
            "total_pagamentos": 0,
            "pagamentos_pix": 0,
            "pagamentos_cartao": 0,
            "pagamentos_dinheiro": 0,
            "valor_pix": 0.0,
            "valor_cartao": 0.0,
            "valor_dinheiro": 0.0,
            "faturamento_por_dia": [],
            "faturamento_por_tipo_vaga": []
        }

    faturamento_total = sum(p.valor_total for p in pagamentos)
    total_pagamentos = len(pagamentos)
    ticket_medio = faturamento_total / total_pagamentos if total_pagamentos > 0 else 0.0

    # Contagem e valor por método de pagamento
    pagamentos_pix = sum(1 for p in pagamentos if p.metodo_pagamento == "pix")
    pagamentos_cartao = sum(1 for p in pagamentos if p.metodo_pagamento == "cartao")
    pagamentos_dinheiro = sum(1 for p in pagamentos if p.metodo_pagamento == "dinheiro")

    valor_pix = sum(p.valor_total for p in pagamentos if p.metodo_pagamento == "pix")
    valor_cartao = sum(p.valor_total for p in pagamentos if p.metodo_pagamento == "cartao")
    valor_dinheiro = sum(p.valor_total for p in pagamentos if p.metodo_pagamento == "dinheiro")

    # Faturamento por dia
    dias = {}
    for p in pagamentos:
        data_str = p.data_pagamento.strftime("%Y-%m-%d")
        if data_str not in dias:
            dias[data_str] = 0.0
        dias[data_str] += p.valor_total

    faturamento_por_dia = [{"data": k, "valor": round(v, 2)} for k, v in sorted(dias.items())]

    # Nome do estacionamento se filtrado
    est_nome = None
    if estacionamento_id:
        est = db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).first()
        if est:
            est_nome = est.nome

    return {
        "periodo": periodo,
        "estacionamento_id": estacionamento_id,
        "estacionamento_nome": est_nome,
        "faturamento_total": round(faturamento_total, 2),
        "ticket_medio": round(ticket_medio, 2),
        "total_pagamentos": total_pagamentos,
        "pagamentos_pix": pagamentos_pix,
        "pagamentos_cartao": pagamentos_cartao,
        "pagamentos_dinheiro": pagamentos_dinheiro,
        "valor_pix": round(valor_pix, 2),
        "valor_cartao": round(valor_cartao, 2),
        "valor_dinheiro": round(valor_dinheiro, 2),
        "faturamento_por_dia": faturamento_por_dia,
        "faturamento_por_tipo_vaga": []
    }
