from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field

from models.db_models import StatusVaga, TipoVaga, StatusReserva


# --- Schemas de Usuário ---
class UsuarioBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    telefone: Optional[str] = None
    placa_veiculo: Optional[str] = Field(None, max_length=10)


class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6)


class UsuarioResponse(UsuarioBase):
    id: str
    is_ativo: bool
    role: str
    estacionamento_id: Optional[str] = None
    criado_em: datetime

    model_config = {"from_attributes": True}


class UsuarioMeResponse(UsuarioResponse):
    """Resposta de /auth/me com o nome do estacionamento vinculado (painel web/mobile)"""

    estacionamento_nome: Optional[str] = None


# --- Schemas de Autenticação ---
class LoginRequest(BaseModel):
    """
    Aceita e-mail OU telefone como credencial de identificação.
    Quando contém "@" é tratado como e-mail; caso contrário compara
    apenas os dígitos com o telefone cadastrado.
    """

    email: str = Field(..., min_length=3, max_length=120)
    senha: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UsuarioResponse] = None


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Schemas de Estacionamento ---
class EstacionamentoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    endereco: Optional[str] = None
    total_andares: int = Field(default=1, ge=1)
    total_vagas: int = Field(default=0, ge=0)
    hora_abertura: Optional[str] = "06:00"
    hora_fechamento: Optional[str] = "22:00"
    taxa_hora: float = Field(default=0.0, ge=0)
    telefone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class EstacionamentoCreate(EstacionamentoBase):
    pass


# --- Schemas de Andar ---
class AndarBase(BaseModel):
    # aceita negativos porque estacionamentos costumam ter subsolos (ex.: -1, -2)
    numero_andar: int = Field(..., ge=-10, le=50)
    capacidade: int = Field(..., ge=1)


class AndarCreate(AndarBase):
    estacionamento_id: str


class AndarResponse(AndarBase):
    id: str
    estacionamento_id: str
    criado_em: datetime
    vagas_livres: Optional[int] = 0
    vagas_ocupadas: Optional[int] = 0

    model_config = {"from_attributes": True}


class EstacionamentoDetalhadoResponse(EstacionamentoBase):
    id: str
    criado_em: datetime
    andares: List[AndarResponse] = []
    vagas_disponiveis_total: Optional[int] = 0

    model_config = {"from_attributes": True}


# --- Schemas de Vaga ---
class VagaBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=10, description="Ex: A1, B12")
    tipo: TipoVaga = TipoVaga.COMUM
    posicao_x: Optional[int] = None
    posicao_y: Optional[int] = None


class VagaCreate(VagaBase):
    andar_id: str


class VagaAtualizaStatus(BaseModel):
    status: StatusVaga
    origem: Optional[str] = Field(
        None,
        pattern="^(sensor|simulador|app_motorista|manual)$",
        description="De onde veio a mudança (feed de eventos do dashboard)",
    )


class VagaLoteStatusUpdate(BaseModel):
    """Atualização de status em lote (simulador de sensores / ações rápidas)"""

    vaga_ids: List[str] = Field(..., min_length=1, max_length=500)
    status: StatusVaga
    origem: Optional[str] = Field(
        None,
        pattern="^(sensor|simulador|app_motorista|manual)$",
        description="De onde veio a mudança (feed de eventos do dashboard)",
    )


class VagaResponse(VagaBase):
    id: str
    andar_id: str
    status: StatusVaga
    numero_andar: Optional[int] = None
    ultima_atualizacao: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MapaVagasResponse(BaseModel):
    estacionamento_id: str
    estacionamento_nome: str
    andares: List[AndarResponse]
    vagas: List[VagaResponse]


class VagaLoteResponse(BaseModel):
    """Resultado de uma atualização de status em lote (simulador de sensores)"""

    solicitadas: int
    atualizadas: int
    nao_encontradas: List[str] = []
    vagas: List[VagaResponse] = []


class ProximaVagaResponse(BaseModel):
    estacionamento_id: str
    vaga: Optional[VagaResponse] = None
    andar_numero: Optional[int] = None
    mensagem: str


# --- Schemas de Reserva ---
class ReservaBase(BaseModel):
    vaga_id: str
    horario_inicio: datetime
    horario_fim: datetime
    observacoes: Optional[str] = None


class ReservaCreate(ReservaBase):
    pass


class ReservaResponse(ReservaBase):
    id: str
    usuario_id: str
    status: StatusReserva
    criado_em: datetime
    vaga: Optional[VagaResponse] = None

    model_config = {"from_attributes": True}


# --- Schemas de Relatórios ---
class FluxoResponse(BaseModel):
    periodo: str
    estacionamento_id: Optional[str] = None
    total_entradas: int
    total_saidas: int
    tempo_medio_permanencia_min: float
    registros: List[dict]


class FluxoPublicoResponse(BaseModel):
    """Versão sem `registros` para telas públicas (Home) — só agregados."""

    periodo: str
    estacionamento_id: Optional[str] = None
    total_entradas: int
    total_saidas: int
    tempo_medio_permanencia_min: float


class OcupacaoResponse(BaseModel):
    periodo: str
    estacionamento_id: Optional[str] = None
    taxa_ocupacao_media: float
    total_vagas: int
    vagas_ocupadas: int
    dados_por_andar: List[dict]


# --- Schemas genéricos ---
class StatusResponse(BaseModel):
    status: str
    versao: str
    ambiente: str
    docs: str


class HealthCheckResponse(BaseModel):
    status: str
    banco_dados: bool


# --- Schemas de Usuário para Admin ---
class UsuarioAdminCreate(UsuarioCreate):
    role: str = "usuario"
    estacionamento_id: Optional[str] = None


class UsuarioAdminUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    placa_veiculo: Optional[str] = None
    role: Optional[str] = None
    is_ativo: Optional[bool] = None
    estacionamento_id: Optional[str] = None


# --- Schemas de Finanças ---
class ConfiguracaoPrecoBase(BaseModel):
    tipo_vaga: str
    valor_hora: float = Field(..., ge=0)
    valor_diaria: Optional[float] = Field(None, ge=0)
    tolerancia_minutos: int = 15


class ConfiguracaoPrecoCreate(ConfiguracaoPrecoBase):
    estacionamento_id: str


class ConfiguracaoPrecoResponse(ConfiguracaoPrecoBase):
    id: str
    estacionamento_id: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class PagamentoResponse(BaseModel):
    id: str
    historico_id: str
    estacionamento_id: str
    valor_total: float
    metodo_pagamento: str
    status_pagamento: str
    data_pagamento: datetime
    comprovante_url: Optional[str] = None
    placa_veiculo: Optional[str] = None
    tempo_permanencia_min: Optional[int] = None

    model_config = {"from_attributes": True}


class ResumoFinanceiroResponse(BaseModel):
    estacionamento_id: Optional[str] = None
    estacionamento_nome: Optional[str] = None
    periodo: str
    faturamento_total: float
    ticket_medio: float
    total_pagamentos: int
    pagamentos_pix: int
    pagamentos_cartao: int
    pagamentos_dinheiro: int
    valor_pix: float
    valor_cartao: float
    valor_dinheiro: float
    faturamento_por_dia: List[dict]
    faturamento_por_tipo_vaga: List[dict]


class RegistrarPagamentoRequest(BaseModel):
    historico_id: str
    metodo_pagamento: str = Field(..., pattern="^(pix|cartao|dinheiro)$")
    valor_total: float = Field(..., gt=0)
    comprovante_url: Optional[str] = None
    observacoes: Optional[str] = None



# --- Schemas do Módulo de Pagamentos ---
class CalcularTarifaRequest(BaseModel):
    cupom_codigo: Optional[str] = None

class PagamentoRequest(BaseModel):
    historico_id: str
    metodo_pagamento: str = Field(..., pattern="^(pix|cartao_credito|cartao_debito|dinheiro)$")
    valor_recebido: Optional[float] = None
    observacoes: Optional[str] = None

class PagamentoResponse(BaseModel):
    id: str
    valor_total: float
    metodo_pagamento: str
    status_pagamento: str
    copia_cola_pix: Optional[str] = None
    qr_code_pix: Optional[str] = None
    link_pagamento: Optional[str] = None
    data_pagamento: Optional[datetime] = None
    troco: Optional[float] = 0.0

    model_config = {"from_attributes": True}

class TarifaResponse(BaseModel):
    historico_id: str
    tempo_permanencia_minutos: int
    valor_bruto: float
    desconto_aplicado: float
    valor_total: float
    cupom_aplicado: Optional[str] = None

class CupomCreate(BaseModel):
    estacionamento_id: str
    codigo: str
    tipo_desconto: str = Field(..., pattern="^(porcentagem|valor_fixo|isencao_total)$")
    valor_desconto: float = Field(..., ge=0)
    descricao: Optional[str] = None
    limite_usos: Optional[int] = None
    data_validade: Optional[datetime] = None

class CupomResponse(BaseModel):
    id: str
    codigo: str
    tipo_desconto: str
    valor_desconto: float
    descricao: Optional[str]
    limite_usos: Optional[int]
    usos_realizados: int
    data_validade: Optional[datetime]
    ativo: bool

    model_config = {"from_attributes": True}

class AbrirCaixaRequest(BaseModel):
    estacionamento_id: str
    valor_inicial: float = 0.0

class FecharCaixaRequest(BaseModel):
    valor_sangria: float = 0.0
    observacoes: Optional[str] = None

class FechamentoCaixaResponse(BaseModel):
    id: str
    data_abertura: datetime
    data_fechamento: Optional[datetime]
    valor_inicial_caixa: float
    valor_pix: float
    valor_cartao_credito: float
    valor_cartao_debito: float
    valor_dinheiro: float
    valor_total: float
    quantidade_pagamentos: int
    valor_sangria: float
    fechado: bool

    model_config = {"from_attributes": True}
