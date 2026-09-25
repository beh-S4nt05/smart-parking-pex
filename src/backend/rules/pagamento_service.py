from datetime import datetime, timedelta
from math import ceil
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.db_models import (
    Historico, Vaga, ConfiguracaoPreco, Pagamento,
    CupomDesconto, FechamentoCaixa,
    StatusPagamento, MetodoPagamento, TipoDesconto, TipoUsuario
)


def calcular_tarifa_estadia(db: Session, historico_id: str, cupom_codigo: Optional[str] = None):
    """
    Calcula o valor total da estadia automaticamente baseado:
    - Tempo de permanência
    - Tipo de vaga e preço configurado
    - Tolerância sem cobrança
    - Valor mínimo se configurado
    - Desconto de cupom se aplicável
    """
    historico = db.query(Historico).filter(Historico.id == historico_id).first()
    if not historico or not historico.saida_em:
        raise HTTPException(status_code=400, detail="Saída não registrada para este veículo")

    if not historico.tempo_permanencia_minutos:
        tempo = int((historico.saida_em - historico.entrada_em).total_seconds() / 60)
        historico.tempo_permanencia_minutos = tempo
    else:
        tempo = historico.tempo_permanencia_minutos

    # Busca configuração de preço para o tipo de vaga
    vaga = db.query(Vaga).filter(Vaga.id == historico.vaga_id).first()
    preco_config = db.query(ConfiguracaoPreco).filter(
        ConfiguracaoPreco.estacionamento_id == historico.estacionamento_id,
        ConfiguracaoPreco.tipo_vaga == vaga.tipo
    ).first()

    if not preco_config:
        raise HTTPException(status_code=400, detail="Preço não configurado para este tipo de vaga")

    # Aplica tolerância
    if tempo <= preco_config.tolerancia_minutos:
        valor_bruto = 0.0
    else:
        tempo_cobrado = tempo - preco_config.tolerancia_minutos

        # Cobrança por hora ou fração de 15 minutos?
        if preco_config.valor_fração_15min:
            # Por fração de 15 minutos
            fracoes = ceil(tempo_cobrado / 15)
            valor_bruto = fracoes * preco_config.valor_fração_15min
        else:
            # Padrão: por hora cheia, com primeira hora proporcional
            horas = ceil(tempo_cobrado / 60)
            # Verifica se tem diária
            if preco_config.valor_diaria and horas >= 9:
                # Acima de 9 horas cobra diária ao invés de hora a hora
                dias = ceil(horas / 24)
                valor_bruto = dias * preco_config.valor_diaria
            else:
                valor_bruto = horas * preco_config.valor_hora

        # Aplica valor mínimo se existir
        if preco_config.cobrar_valor_minimo and preco_config.valor_minimo and valor_bruto < preco_config.valor_minimo:
            valor_bruto = preco_config.valor_minimo

    # Aplica cupom de desconto se enviado
    valor_desconto = 0.0
    if cupom_codigo:
        cupom = db.query(CupomDesconto).filter(
            CupomDesconto.codigo == cupom_codigo.strip().upper(),
            CupomDesconto.estacionamento_id == historico.estacionamento_id,
            CupomDesconto.ativo == True
        ).first()

        if not cupom:
            raise HTTPException(status_code=400, detail="Cupom inválido ou não existe")

        if cupom.data_validade and cupom.data_validade < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Cupom expirado")

        if cupom.limite_usos is not None and cupom.usos_realizados >= cupom.limite_usos:
            raise HTTPException(status_code=400, detail="Cupom atingiu o limite de usos")

        if cupom.tipo_desconto == TipoDesconto.ISENCAO_TOTAL.value:
            valor_desconto = valor_bruto
            historico.status_pagamento = StatusPagamento.PAGO
        elif cupom.tipo_desconto == TipoDesconto.PORCENTAGEM.value:
            valor_desconto = round(valor_bruto * (cupom.valor_desconto / 100), 2)
        elif cupom.tipo_desconto == TipoDesconto.VALOR_FIXO.value:
            valor_desconto = min(cupom.valor_desconto, valor_bruto)

        cupom.usos_realizados += 1
        historico.cupom_aplicado = cupom.codigo

    valor_total = round(max(valor_bruto - valor_desconto, 0.0), 2)

    historico.valor_bruto = round(valor_bruto, 2)
    historico.valor_desconto = round(valor_desconto, 2)
    historico.valor_total = valor_total
    db.commit()

    return {
        "historico_id": historico.id,
        "tempo_permanencia_minutos": tempo,
        "valor_bruto": round(valor_bruto,2),
        "desconto_aplicado": round(valor_desconto,2),
        "valor_total": valor_total,
        "cupom_aplicado": historico.cupom_aplicado
    }


def registrar_pagamento(
    db: Session,
    historico_id: str,
    metodo_pagamento: str,
    valor_recebido: Optional[float] = None,
    observacoes: Optional[str] = None,
    usuario_operador=None
):
    """
    Registra pagamento presencial (dinheiro/cartão)
    """
    historico = db.query(Historico).filter(Historico.id == historico_id).first()
    if not historico:
        raise HTTPException(status_code=404, detail="Registro de estadia não encontrado")

    if historico.status_pagamento == StatusPagamento.PAGO:
        raise HTTPException(status_code=400, detail="Este ticket já está pago")

    valor_total = historico.valor_total
    troco = 0.0
    if metodo_pagamento == MetodoPagamento.DINHEIRO.value and valor_recebido is not None:
        if valor_recebido < valor_total:
            raise HTTPException(status_code=400, detail=f"Valor recebido é menor que o total (R$ {valor_total})")
        troco = round(valor_recebido - valor_total, 2)

    # Cria registro de pagamento
    novo_pagamento = Pagamento(
        historico_id=historico_id,
        estacionamento_id=historico.estacionamento_id,
        usuario_id=historico.usuario_id,
        valor_bruto=historico.valor_bruto,
        valor_desconto=historico.valor_desconto,
        valor_total=valor_total,
        metodo_pagamento=metodo_pagamento,
        status_pagamento=StatusPagamento.PAGO,
        data_pagamento=datetime.utcnow(),
        observacoes=observacoes
    )
    db.add(novo_pagamento)
    db.flush()

    historico.pagamento_id = novo_pagamento.id
    historico.status_pagamento = StatusPagamento.PAGO
    historico.forma_pagamento = metodo_pagamento
    db.commit()
    db.refresh(novo_pagamento)

    # Atualiza caixa aberto
    caixa_aberto = db.query(FechamentoCaixa).filter(
        FechamentoCaixa.estacionamento_id == historico.estacionamento_id,
        FechamentoCaixa.fechado == False
    ).first()

    if caixa_aberto:
        if metodo_pagamento == MetodoPagamento.PIX.value:
            caixa_aberto.valor_pix += valor_total
        elif metodo_pagamento == MetodoPagamento.CARTAO_CREDITO.value:
            caixa_aberto.valor_cartao_credito += valor_total
        elif metodo_pagamento == MetodoPagamento.CARTAO_DEBITO.value:
            caixa_aberto.valor_cartao_debito += valor_total
        elif metodo_pagamento == MetodoPagamento.DINHEIRO.value:
            caixa_aberto.valor_dinheiro += valor_total
        caixa_aberto.valor_total += valor_total
        caixa_aberto.quantidade_pagamentos += 1
        caixa_aberto.valor_descontos += historico.valor_desconto or 0
        db.commit()

    return {
        "pagamento": novo_pagamento,
        "troco": troco,
        "mensagem": "Pagamento registrado com sucesso"
    }


def gerar_pagamento_pix(db: Session, historico_id: str):
    """
    Simula geração de QR Code PIX para pagamento pelo app.
    Em produção integre com Mercado Pago, Gerencianet, Pix Efí etc.
    """
    historico = db.query(Historico).filter(Historico.id == historico_id).first()
    if not historico:
        raise HTTPException(status_code=404, detail="Estadia não encontrada")
    if historico.valor_total is None:
        calcular_tarifa_estadia(db, historico_id)
        db.refresh(historico)

    novo_pagamento = Pagamento(
        historico_id=historico_id,
        estacionamento_id=historico.estacionamento_id,
        usuario_id=historico.usuario_id,
        valor_bruto=historico.valor_bruto,
        valor_desconto=historico.valor_desconto,
        valor_total=historico.valor_total,
        metodo_pagamento=MetodoPagamento.PIX.value,
        status_pagamento=StatusPagamento.PENDENTE,
        gateway_pagamento="pix_simulado",
        copia_cola_pix=f"PIX_SIMULADO_{historico.id}_VALOR_{historico.valor_total}",
        qr_code_pix=f"data:image/png;base64,QRCODE_SIMULADO",
        link_pagamento=f"https://seupagamento.com/pay/{historico.id}"
    )
    db.add(novo_pagamento)
    db.commit()
    db.refresh(novo_pagamento)

    historico.pagamento_id = novo_pagamento.id
    historico.forma_pagamento = MetodoPagamento.PIX.value
    db.commit()

    return novo_pagamento


def confirmar_pagamento_online(db: Session, pagamento_id: str):
    """Webhook para confirmação de pagamento online (PIX/Cartão) pelo gateway"""
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    if pagamento.status_pagamento == StatusPagamento.PAGO:
        return pagamento

    pagamento.status_pagamento = StatusPagamento.PAGO
    pagamento.data_pagamento = datetime.utcnow()

    historico = db.query(Historico).filter(Historico.id == pagamento.historico_id).first()
    historico.status_pagamento = StatusPagamento.PAGO
    db.commit()
    db.refresh(pagamento)
    return pagamento


def abrir_caixa(db: Session, estacionamento_id: str, valor_inicial: float, usuario_operador):
    """Abre um novo caixa para o turno"""
    # Verifica se já tem caixa aberto
    caixa_existente = db.query(FechamentoCaixa).filter(
        FechamentoCaixa.estacionamento_id == estacionamento_id,
        FechamentoCaixa.fechado == False
    ).first()
    if caixa_existente:
        raise HTTPException(status_code=400, detail="Já existe um caixa aberto para este estacionamento")

    novo_caixa = FechamentoCaixa(
        estacionamento_id=estacionamento_id,
        usuario_abertura_id=usuario_operador.id,
        valor_inicial_caixa=valor_inicial
    )
    db.add(novo_caixa)
    db.commit()
    db.refresh(novo_caixa)
    return novo_caixa


def fechar_caixa(db: Session, caixa_id: str, valor_sangria: float, observacoes: Optional[str], usuario_operador):
    """Fecha o caixa do turno, consolida todos valores"""
    caixa = db.query(FechamentoCaixa).filter(FechamentoCaixa.id == caixa_id).first()
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    if caixa.fechado:
        raise HTTPException(status_code=400, detail="Este caixa já está fechado")

    caixa.data_fechamento = datetime.utcnow()
    caixa.usuario_fechamento_id = usuario_operador.id
    caixa.valor_sangria = valor_sangria
    caixa.observacoes = observacoes
    caixa.fechado = True
    caixa.valor_total = round(caixa.valor_pix + caixa.valor_cartao_credito + caixa.valor_cartao_debito + caixa.valor_dinheiro, 2)
    db.commit()
    db.refresh(caixa)
    return caixa


def listar_cupons_estacionamento(db: Session, estacionamento_id: str):
    return db.query(CupomDesconto).filter(CupomDesconto.estacionamento_id == estacionamento_id).all()


def criar_cupom(db: Session, dados: dict):
    cupom = CupomDesconto(**dados)
    cupom.codigo = cupom.codigo.strip().upper()
    db.add(cupom)
    db.commit()
    db.refresh(cupom)
    return cupom
