from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.config import settings
from core.deps import get_usuario_admin, get_usuario_financeiro, get_usuario_gestor, permissao_necessaria, get_usuario_autenticado
from core.deps import garantir_escopo_estacionamento
from models.database import get_db
from models.db_models import Usuario, Estacionamento, Andar, Vaga, TipoUsuario, FechamentoCaixa, Historico, Pagamento
from models.schemas import (
    EstacionamentoDetalhadoResponse as EstacionamentoResponse,
    EstacionamentoCreate,
    AndarResponse, AndarCreate,
    VagaResponse, VagaCreate,
    UsuarioResponse, UsuarioAdminCreate, UsuarioAdminUpdate,
    ConfiguracaoPrecoResponse, ConfiguracaoPrecoCreate,
    PagamentoResponse,
    ResumoFinanceiroResponse
)
from rules import admin_service, estacionamento_service, financeiro_service, simulador_service, eventos_service

router = APIRouter(prefix="/api/admin", tags=["Painel Administrativo"])


# Schemas para atualizações do admin
class EstacionamentoUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    total_andares: Optional[int] = None
    total_vagas: Optional[int] = None
    hora_abertura: Optional[str] = None
    hora_fechamento: Optional[str] = None
    taxa_hora: Optional[float] = None
    telefone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LoteVagasCreate(BaseModel):
    andar_id: str
    quantidade: int
    prefixo_codigo: str = ""
    tipo: str = "comum"  # ACH-17: sem isto o lote só criava "comum"


# ======================================================================
# ROTAS DE ESTACIONAMENTOS (admin)
# ======================================================================
@router.post("/estacionamentos", response_model=EstacionamentoResponse, status_code=201)
async def criar_estacionamento(
    dados: EstacionamentoCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Cria um novo estacionamento (apenas admin)"""
    return admin_service.criar_estacionamento(db, dados)


@router.put("/estacionamentos/{id}", response_model=EstacionamentoResponse)
async def atualizar_estacionamento(
    id: str,
    dados: EstacionamentoUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Atualiza dados de um estacionamento (apenas admin)"""
    return admin_service.atualizar_estacionamento(db, id, dados.model_dump(exclude_unset=True))


@router.delete("/estacionamentos/{id}")
async def deletar_estacionamento(
    id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Remove um estacionamento e todos os seus andares/vagas (apenas admin)"""
    return admin_service.deletar_estacionamento(db, id)


# ======================================================================
# ROTAS DE ANDARES (admin)
# ======================================================================
@router.post("/andares", response_model=AndarResponse, status_code=201)
async def criar_andar(
    dados: AndarCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Adiciona um novo andar a um estacionamento (apenas admin)"""
    return admin_service.criar_andar(db, dados)


@router.delete("/andares/{id}")
async def deletar_andar(
    id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Remove um andar e todas as suas vagas (apenas admin)"""
    return admin_service.deletar_andar(db, id)


# ======================================================================
# ROTAS DE VAGAS (admin)
# ======================================================================
class AndarUpdate(BaseModel):
    numero_andar: Optional[int] = None
    capacidade: Optional[int] = Field(None, ge=1, le=2000)


@router.put("/andares/{id}", response_model=AndarResponse)
async def atualizar_andar(
    id: str,
    dados: AndarUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    """RF-32: editar número/capacidade de um andar (admin)."""
    return admin_service.atualizar_andar(db, id, dados.model_dump(exclude_unset=True))


class VagaAdminUpdate(BaseModel):
    codigo: Optional[str] = None
    tipo: Optional[str] = None
    posicao_x: Optional[int] = None
    posicao_y: Optional[int] = None


@router.put("/vagas/{id}", response_model=VagaResponse)
async def atualizar_vaga_admin(
    id: str,
    dados: VagaAdminUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    """RF-33: editar código/tipo/posição de uma vaga sem tocar no status."""
    return admin_service.atualizar_vaga(db, id, dados.model_dump(exclude_unset=True))


@router.post("/usuarios/{id}/reset-senha")
async def reset_senha_usuario(
    id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    """
    RF-14 (sem SMTP): gera senha temporária de balcão e derruba todas as
    sessões do usuário. Mostre ao dono da conta por um canal combinado; ele
    troca em "Minha conta" no primeiro login.
    """
    temporaria = admin_service.reset_senha_admin(db, id)
    return {"senha_temporaria": temporaria,
            "aviso": "Entregue em mãos e peça a troca imediata em Perfil → Segurança."}


# ------------------- Sensores físicos (RF-45 · ADR-03) — emissão só admin -------------------
from rules import sensor_service  # noqa: E402


class SensorCreate(BaseModel):
    estacionamento_id: str
    codigo: str
    nome: Optional[str] = None


@router.post("/sensores", status_code=201)
async def emitir_sensor(
    dados: SensorCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    """Emite um dispositivo e a ÚNICA exibição da chave clara (SHA-256 no banco)."""
    sensor, chave = sensor_service.emitir_sensor(
        db, dados.estacionamento_id, dados.codigo, dados.nome
    )
    return {
        "id": sensor.id, "codigo": sensor.codigo, "nome": sensor.nome,
        "chave": chave,
        "aviso": "Guarde agora — não há como recuperar. Em caso de perda: revogar e reemitir.",
    }


@router.get("/sensores")
async def listar_sensores(
    estacionamento_id: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    q = db.query(sensor_service.Sensor)
    if estacionamento_id:
        q = q.filter(sensor_service.Sensor.estacionamento_id == estacionamento_id)
    return [
        {
            "id": x.id, "codigo": x.codigo, "nome": x.nome, "ativo": x.ativo,
            "estacionamento_id": x.estacionamento_id,
            "ultimo_evento_em": x.ultimo_evento_em.isoformat() if x.ultimo_evento_em else None,
        }
        for x in q.order_by(sensor_service.Sensor.codigo).all()
    ]


@router.post("/sensores/{id}/revogar")
async def revogar_sensor(
    id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    """Desativa o dispositivo — eventos futuros com a chave antiga dão 401."""
    sensor = db.query(sensor_service.Sensor).filter(sensor_service.Sensor.id == id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor não encontrado")
    sensor.ativo = False
    db.commit()
    return {"mensagem": f"Sensor {sensor.codigo} revogado"}


@router.post("/vagas", response_model=VagaResponse, status_code=201)
async def criar_vaga(
    dados: VagaCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Cria uma nova vaga individual (apenas admin)"""
    return admin_service.criar_vaga(db, dados)


@router.post("/vagas/lote", response_model=List[VagaResponse], status_code=201)
async def criar_vagas_em_lote(
    dados: LoteVagasCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """
    Cria várias vagas de uma vez em um andar (cadastro rápido):
    Gera automaticamente códigos sequenciais: A01, A02, A03...
    """
    return admin_service.criar_vagas_em_lote(
        db,
        andar_id=dados.andar_id,
        quantidade=dados.quantidade,
        prefixo_codigo=dados.prefixo_codigo,
        tipo=dados.tipo,
    )


@router.delete("/vagas/{id}")
async def deletar_vaga(
    id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Remove uma vaga (apenas admin)"""
    return admin_service.deletar_vaga(db, id)


# ======================================================================
# ROTAS DE GERENCIAMENTO DE USUÁRIOS (admin)
# ======================================================================
@router.post("/usuarios", response_model=UsuarioResponse, status_code=201)
async def criar_usuario(
    dados: UsuarioAdminCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Cria um novo usuário com qualquer cargo (público, usuario, financeiro, gestor, admin) - APENAS ADMIN GLOBAL"""
    return admin_service.criar_usuario_admin(db, dados)


@router.put("/usuarios/{id}", response_model=UsuarioResponse)
async def atualizar_usuario(
    id: str,
    dados: UsuarioAdminUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Atualiza dados e permissões de qualquer usuário - APENAS ADMIN GLOBAL"""
    return admin_service.atualizar_usuario_admin(db, id, dados)


@router.get("/usuarios", response_model=List[UsuarioResponse])
async def listar_todos_usuarios(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Lista todos os usuários cadastrados no sistema (apenas admin)"""
    return admin_service.listar_todos_usuarios(db)


@router.patch("/usuarios/{id}/ativar-desativar", response_model=UsuarioResponse)
async def alternar_status_usuario(
    id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Ativa/desativa um usuário (não funciona com admins)"""
    return admin_service.alternar_status_usuario(db, id)


@router.patch("/usuarios/{id}/promover-admin", response_model=UsuarioResponse)
async def promover_admin(
    id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """Promove um usuário comum para cargo de administrador"""
    return admin_service.promover_usuario_admin(db, id)


@router.get("/dashboard")
async def dashboard_admin(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin)
):
    """
    Dados consolidados para o dashboard inicial do painel administrativo
    Retorna contadores gerais do sistema
    """
    total_estacionamentos = db.query(Estacionamento).count()
    total_usuarios = db.query(Usuario).filter(Usuario.role == "usuario").count()
    total_andares = db.query(Andar).count()

    from models.db_models import Vaga, StatusVaga, Reserva
    total_vagas = db.query(Vaga).count()
    vagas_ocupadas = db.query(Vaga).filter(Vaga.status == StatusVaga.OCUPADA).count()
    vagas_reservadas = db.query(Vaga).filter(Vaga.status == StatusVaga.RESERVADA).count()
    vagas_livres = db.query(Vaga).filter(Vaga.status == StatusVaga.LIVRE).count()

    total_reservas_hoje = db.query(Reserva).filter(
        func.date(Reserva.criado_em) == func.date(func.now())
    ).count()

    return {
        "total_estacionamentos": total_estacionamentos,
        "total_usuarios_cadastrados": total_usuarios,
        "total_andares": total_andares,
        "total_vagas": total_vagas,
        "ocupacao_atual": {
            "livres": vagas_livres,
            "ocupadas": vagas_ocupadas,
            "reservadas": vagas_reservadas,
            "taxa_ocupacao_percentual": round(((vagas_ocupadas + vagas_reservadas) / total_vagas * 100), 2) if total_vagas > 0 else 0
        },
        "reservas_hoje": total_reservas_hoje
    }


# ======================================================================
# 📱 SIMULADOR DE SENSORES (QR Code / sessões via token)
# ======================================================================
class SimuladorSessaoCreate(BaseModel):
    estacionamento_id: str
    andar_numero: Optional[int] = None
    expira_em_horas: Optional[int] = 12


@router.post("/simulador/sessoes", status_code=201)
async def criar_sessao_simulador(
    dados: SimuladorSessaoCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_admin),
):
    """
    Gera uma sessão do simulador para um estacionamento (e andar opcional):
    retorna URL tokenizada + QR Code em data-URL PNG, revogável e com expiração.
    Acesso: somente o administrador global (simulação de vagas é tooling de
    infraestrutura de sensores — gestores não operam).
    """
    return simulador_service.criar_sessao(
        db,
        estacionamento_id=dados.estacionamento_id,
        andar_numero=dados.andar_numero,
        expira_em_horas=dados.expira_em_horas or 12,
        base_url=settings.SIMULADOR_BASE_URL,
    )


@router.get("/simulador/sessoes")
async def listar_sessoes_simulador(
    usuario: Usuario = Depends(get_usuario_admin),
):
    """Lista as sessões ativas do simulador (expiração e local). Acesso: Admin global."""
    return simulador_service.listar_sessoes_ativas()


@router.delete("/simulador/sessoes/{token}")
async def revogar_sessao_simulador(
    token: str,
    usuario: Usuario = Depends(get_usuario_admin),
):
    """Revoga uma sessão do simulador (o link do celular para de funcionar)."""
    return simulador_service.revogar_sessao(token)


@router.get("/simulador/sessoes/{token}/validar")
async def validar_sessao_simulador(token: str):
    """
    Consulta pública do estado da sessão (o token de 13 chars + expiração é o
    segredo). A rota /simulador do app só deixa operar quem tem JWT de
    administrador global — quem criou a sessão, usa o simulador.
    """
    return simulador_service.validar_sessao(token)


# ======================================================================
#  FEED DE EVENTOS (dashboard "Últimos eventos de vagas")
# ======================================================================
@router.get("/eventos")
async def eventos_recentes(
    estacionamento_id: Optional[str] = None,
    limite: int = 8,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_gestor),
):
    """Últimas movimentações de vagas com origem (sensor/simulador/app)."""
    # ACH-16/ADR-07: gestor/financeiro veem SÓ o próprio estacionamento
    estacionamento_id = garantir_escopo_estacionamento(usuario, estacionamento_id, "ver eventos deste estacionamento")
    return eventos_service.listar_eventos_recentes(db, estacionamento_id, limite)


@router.get("/ocupacao-andares/{estacionamento_id}")
async def ocupacao_por_andar(
    estacionamento_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_gestor),
):
    """Percentual de ocupação por andar — barras do dashboard."""
    garantir_escopo_estacionamento(usuario, estacionamento_id, "ver ocupação deste estacionamento")
    return eventos_service.ocupacao_por_andar(db, estacionamento_id)


# ======================================================================
# 📊 ROTAS FINANCEIRAS (acesso para Admin, Gestor e Financeiro)
# ======================================================================
@router.post("/financeiro/precos", response_model=ConfiguracaoPrecoResponse, status_code=201)
async def configurar_preco_vaga(
    dados: ConfiguracaoPrecoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_gestor)
):
    """
    Configura/atualiza preço por tipo de vaga em um estacionamento.
    Acesso: Admin e Gestor (gestor só no SEU estacionamento — ADR-07)
    """
    dados.estacionamento_id = garantir_escopo_estacionamento(
        usuario, dados.estacionamento_id, "configurar preços deste estacionamento"
    ) or dados.estacionamento_id
    return financeiro_service.criar_configuracao_preco(db, dados)


@router.get("/financeiro/precos/{estacionamento_id}", response_model=List[ConfiguracaoPrecoResponse])
async def listar_precos_estacionamento(
    estacionamento_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """
    Lista todos os preços configurados para um estacionamento.
    Acesso: Admin, Gestor e Financeiro (escopo próprio — ADR-07)
    """
    estacionamento_id = garantir_escopo_estacionamento(
        usuario, estacionamento_id, "ver preços deste estacionamento"
    )
    return financeiro_service.listar_precos_estacionamento(db, estacionamento_id)


# (removido, ADR-08/P14: este POST chamava financeiro_service.registrar_pagamento,
#  que gravava `comprovante_url` — coluna que NÃO existe em Pagamentos — e quebrava
#  com 500. O fluxo real e testável de pagamento é POST /financeiro/pagamento/registrar)


@router.get("/financeiro/pagamentos/{estacionamento_id}", response_model=List[PagamentoResponse])
async def listar_pagamentos(
    estacionamento_id: str,
    periodo: str = "diario",
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """
    Lista todos os pagamentos de um estacionamento no período.
    Acesso: Admin, Gestor e Financeiro (escopo próprio — ADR-07)
    """
    estacionamento_id = garantir_escopo_estacionamento(
        usuario, estacionamento_id, "ver pagamentos deste estacionamento"
    )
    return financeiro_service.listar_pagamentos_estacionamento(db, estacionamento_id, periodo)


@router.get("/financeiro/resumo", response_model=ResumoFinanceiroResponse)
async def resumo_financeiro(
    periodo: str = "diario",
    estacionamento_id: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """
    Retorna resumo completo de faturamento do período:
    - Faturamento total
    - Ticket médio
    - Quantidade e valor por método de pagamento
    - Faturamento por dia
    Acesso: Admin, Gestor e Financeiro
    """
    return financeiro_service.obter_resumo_financeiro(db, periodo, estacionamento_id, usuario)


@router.get("/gestor/dashboard")
async def dashboard_gestor(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_gestor)
):
    """
    Dashboard para gestores e financeiro, mostra dados APENAS do estacionamento que eles gerenciam.
    Se for Admin sem estacionamento vinculado, retorna erro orientando a selecionar um estacionamento.
    Acesso: Gestor e Financeiro
    """
    est_id = usuario.estacionamento_id
    if not est_id and usuario.role == TipoUsuario.ADMIN.value:
        return {
            "mensagem": "Selecione um estacionamento para ver o dashboard",
            "estacionamento": None,
            "ocupacao": None,
            "faturamento_hoje": 0,
            "ticket_medio_hoje": 0,
            "total_pagamentos_hoje": 0
        }

    est = db.query(Estacionamento).filter(Estacionamento.id == est_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estacionamento vinculado ao usuário não encontrado")

    total_vagas = db.query(Vaga).join(Andar).filter(Andar.estacionamento_id == est_id).count()
    vagas_ocupadas = db.query(Vaga).join(Andar).filter(
        Andar.estacionamento_id == est_id,
        Vaga.status == "ocupada"
    ).count()
    vagas_reservadas = db.query(Vaga).join(Andar).filter(
        Andar.estacionamento_id == est_id,
        Vaga.status == "reservada"
    ).count()
    vagas_livres = total_vagas - vagas_ocupadas - vagas_reservadas

    resumo_hoje = financeiro_service.obter_resumo_financeiro(db, "diario", est_id, usuario)

    return {
        "estacionamento": {
            "id": est.id,
            "nome": est.nome,
            "endereco": est.endereco
        },
        "ocupacao": {
            "total_vagas": total_vagas,
            "livres": vagas_livres,
            "ocupadas": vagas_ocupadas,
            "reservadas": vagas_reservadas,
            "taxa_ocupacao_percentual": round(((vagas_ocupadas + vagas_reservadas) / total_vagas * 100), 2) if total_vagas > 0 else 0
        },
        "faturamento_hoje": resumo_hoje["faturamento_total"],
        "ticket_medio_hoje": resumo_hoje["ticket_medio"],
        "total_pagamentos_hoje": resumo_hoje["total_pagamentos"]
    }


# ======================================================================
# 💰 ROTAS DO MÓDULO DE PAGAMENTOS E FATURAMENTO
# ======================================================================
from models.schemas import (
    TarifaResponse, CalcularTarifaRequest,
    PagamentoRequest, PagamentoResponse as PagamentoResponseSchema,
    CupomCreate, CupomResponse,
    AbrirCaixaRequest, FecharCaixaRequest, FechamentoCaixaResponse
)
from rules import pagamento_service

@router.post("/financeiro/calcular-tarifa", response_model=TarifaResponse)
async def calcular_tarifa(
    historico_id: str,
    dados: CalcularTarifaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """Calcula valor da tarifa de estadia, aplicando cupom se fornecido.
    O consumo do cupom (RF: limite de usos) acontece SÓ no registrar (ACH-07)."""
    hist = db.query(Historico).filter(Historico.id == historico_id).first()
    if not hist:
        raise HTTPException(status_code=404, detail="Estadia não encontrada")
    garantir_escopo_estacionamento(usuario, hist.estacionamento_id, "cobrar esta estadia")
    return pagamento_service.calcular_tarifa_estadia(db, historico_id, dados.cupom_codigo)


@router.post("/financeiro/pagamento/registrar", response_model=PagamentoResponseSchema)
async def registrar_pagamento_presencial(
    dados: PagamentoRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """Registra pagamento presencial em dinheiro ou cartão no caixa"""
    hist = db.query(Historico).filter(Historico.id == dados.historico_id).first()
    if not hist:
        raise HTTPException(status_code=404, detail="Estadia não encontrada")
    garantir_escopo_estacionamento(usuario, hist.estacionamento_id, "registrar pagamento desta estadia")
    result = pagamento_service.registrar_pagamento(db, dados.historico_id, dados.metodo_pagamento, dados.valor_recebido, dados.observacoes, usuario)
    return {
        "id": result["pagamento"].id,
        "valor_total": result["pagamento"].valor_total,
        "metodo_pagamento": result["pagamento"].metodo_pagamento,
        "status_pagamento": result["pagamento"].status_pagamento,
        "data_pagamento": result["pagamento"].data_pagamento,
        "troco": result["troco"]
    }


@router.post("/financeiro/pagamento/gerar-pix", response_model=PagamentoResponseSchema)
async def gerar_qr_pix(
    historico_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_autenticado)
):
    """Gera QR Code PIX para pagamento pelo app"""
    hist = db.query(Historico).filter(Historico.id == historico_id).first()
    if not hist:
        raise HTTPException(status_code=404, detail="Estadia não encontrada")
    if usuario.role == TipoUsuario.ADMIN.value:
        pass
    elif usuario.role in (TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value):
        garantir_escopo_estacionamento(usuario, hist.estacionamento_id, "cobrar esta estadia")
    elif hist.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="Esta estadia não pertence a você")
    pagamento = pagamento_service.gerar_pagamento_pix(db, historico_id)
    return {
        "id": pagamento.id,
        "valor_total": pagamento.valor_total,
        "metodo_pagamento": pagamento.metodo_pagamento,
        "status_pagamento": pagamento.status_pagamento,
        "copia_cola_pix": pagamento.copia_cola_pix,
        "qr_code_pix": pagamento.qr_code_pix,
        "link_pagamento": pagamento.link_pagamento,
        "data_pagamento": None,
        "troco": 0.0
    }


@router.post("/financeiro/pagamento/{id}/confirmar")
async def confirmar_pagamento(
    id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """Confirma pagamento (webhook ou confirmação manual)"""
    pag = db.query(Pagamento).filter(Pagamento.id == id).first()
    if not pag:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    garantir_escopo_estacionamento(usuario, pag.estacionamento_id, "confirmar este pagamento")
    return pagamento_service.confirmar_pagamento_online(db, id)


@router.post("/financeiro/caixa/abrir", response_model=FechamentoCaixaResponse)
async def abrir_caixa(
    dados: AbrirCaixaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """Abre um novo caixa para início de turno"""
    dados.estacionamento_id = garantir_escopo_estacionamento(
        usuario, dados.estacionamento_id, "abrir caixa deste estacionamento"
    ) or dados.estacionamento_id
    return pagamento_service.abrir_caixa(db, dados.estacionamento_id, dados.valor_inicial, usuario)


@router.post("/financeiro/caixa/{id}/fechar", response_model=FechamentoCaixaResponse)
async def fechar_caixa(
    id: str,
    dados: FecharCaixaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """Fecha o caixa com valores consolidados"""
    caixa = db.query(FechamentoCaixa).filter(FechamentoCaixa.id == id).first()
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    garantir_escopo_estacionamento(usuario, caixa.estacionamento_id, "fechar este caixa")
    return pagamento_service.fechar_caixa(db, id, dados.valor_sangria, dados.observacoes, usuario)


@router.get("/financeiro/caixa/aberto/{estacionamento_id}", response_model=Optional[FechamentoCaixaResponse])
async def obter_caixa_aberto(
    estacionamento_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_financeiro)
):
    """Retorna o caixa aberto atualmente no estacionamento"""
    garantir_escopo_estacionamento(usuario, estacionamento_id, "ver caixa deste estacionamento")
    return db.query(FechamentoCaixa).filter(
        FechamentoCaixa.estacionamento_id == estacionamento_id,
        FechamentoCaixa.fechado == False
    ).first()


@router.post("/financeiro/cupons", response_model=CupomResponse, status_code=201)
async def criar_cupom_desconto(
    dados: CupomCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_gestor)
):
    """Cria um novo cupom de desconto"""
    # ADR-07: gestor só cria cupom para o SEU estacionamento (admin global)
    dados.estacionamento_id = garantir_escopo_estacionamento(
        admin, dados.estacionamento_id, "criar cupom neste estacionamento"
    ) or dados.estacionamento_id
    return pagamento_service.criar_cupom(db, dados.model_dump())


@router.get("/financeiro/cupons/{estacionamento_id}", response_model=List[CupomResponse])
async def listar_cupons(
    estacionamento_id: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_usuario_financeiro)
):
    """Lista todos cupons do estacionamento"""
    estacionamento_id = garantir_escopo_estacionamento(
        admin, estacionamento_id, "ver cupons deste estacionamento"
    )
    return pagamento_service.listar_cupons_estacionamento(db, estacionamento_id)
