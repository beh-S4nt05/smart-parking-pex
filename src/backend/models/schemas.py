from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from models.db_models import StatusReserva, StatusVaga, TipoVaga


# --- Schemas de Usuário ---
class UsuarioBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    telefone: str | None = None
    placa_veiculo: str | None = Field(None, max_length=10)
    # RF-47: autodeclaração PCD (cadastro/perfil). False = motorista comum.
    is_pcd: bool = False


class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6)


class UsuarioResponse(UsuarioBase):
    id: str
    is_ativo: bool
    role: str
    estacionamento_id: str | None = None
    criado_em: datetime

    model_config = {"from_attributes": True}


class UsuarioMeResponse(UsuarioResponse):
    """Resposta de /auth/me com o nome do estacionamento vinculado (painel web/mobile)"""

    estacionamento_nome: str | None = None


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
    user: UsuarioResponse | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Schemas de Estacionamento ---
class EstacionamentoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    endereco: str | None = None
    total_andares: int = Field(default=1, ge=1)
    total_vagas: int = Field(default=0, ge=0)
    hora_abertura: str | None = "06:00"
    hora_fechamento: str | None = "22:00"
    taxa_hora: float = Field(default=0.0, ge=0)
    telefone: str | None = None
    latitude: float | None = None
    longitude: float | None = None


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
    vagas_livres: int | None = 0
    vagas_ocupadas: int | None = 0

    model_config = {"from_attributes": True}


class EstacionamentoDetalhadoResponse(EstacionamentoBase):
    id: str
    criado_em: datetime
    andares: list[AndarResponse] = []
    vagas_disponiveis_total: int | None = 0

    model_config = {"from_attributes": True}


# --- Schemas de Vaga ---
class VagaBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=10, description="Ex: A1, B12")
    tipo: TipoVaga = TipoVaga.COMUM
    posicao_x: int | None = None
    posicao_y: int | None = None


class VagaCreate(VagaBase):
    andar_id: str


class VagaAtualizaStatus(BaseModel):
    status: StatusVaga
    origem: str | None = Field(
        None,
        pattern="^(sensor|simulador|app_motorista|manual)$",
        description="De onde veio a mudança (feed de eventos do dashboard)",
    )


class VagaLoteStatusUpdate(BaseModel):
    """Atualização de status em lote (simulador de sensores / ações rápidas)"""

    vaga_ids: list[str] = Field(..., min_length=1, max_length=500)
    status: StatusVaga
    origem: str | None = Field(
        None,
        pattern="^(sensor|simulador|app_motorista|manual)$",
        description="De onde veio a mudança (feed de eventos do dashboard)",
    )


class VagaResponse(VagaBase):
    id: str
    andar_id: str
    status: StatusVaga
    numero_andar: int | None = None
    ultima_atualizacao: datetime | None = None

    model_config = {"from_attributes": True}


class MapaVagasResponse(BaseModel):
    estacionamento_id: str
    estacionamento_nome: str
    andares: list[AndarResponse]
    vagas: list[VagaResponse]


class VagaLoteResponse(BaseModel):
    """Resultado de uma atualização de status em lote (simulador de sensores)"""

    solicitadas: int
    atualizadas: int
    nao_encontradas: list[str] = []
    vagas: list[VagaResponse] = []


class ProximaVagaResponse(BaseModel):
    estacionamento_id: str
    vaga: VagaResponse | None = None
    andar_numero: int | None = None
    mensagem: str
    # RF-47: presente quando a elegibilidade PCD alterou a atribuição
    aviso: str | None = None


# --- Schemas de Reserva ---
class ReservaBase(BaseModel):
    vaga_id: str
    horario_inicio: datetime
    horario_fim: datetime
    observacoes: str | None = None


class ReservaCreate(ReservaBase):
    pass


class ReservaResponse(ReservaBase):
    id: str
    usuario_id: str
    status: StatusReserva
    criado_em: datetime
    vaga: VagaResponse | None = None

    model_config = {"from_attributes": True}


# --- Schemas de Relatórios ---
class FluxoResponse(BaseModel):
    periodo: str
    estacionamento_id: str | None = None
    total_entradas: int
    total_saidas: int
    tempo_medio_permanencia_min: float
    registros: list[dict]


class FluxoPublicoResponse(BaseModel):
    """Versão sem `registros` para telas públicas (Home) — só agregados."""

    periodo: str
    estacionamento_id: str | None = None
    total_entradas: int
    total_saidas: int
    tempo_medio_permanencia_min: float


class OcupacaoResponse(BaseModel):
    periodo: str
    estacionamento_id: str | None = None
    taxa_ocupacao_media: float
    total_vagas: int
    vagas_ocupadas: int
    dados_por_andar: list[dict]


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
    estacionamento_id: str | None = None


class UsuarioAdminUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    placa_veiculo: str | None = None
    role: str | None = None
    is_ativo: bool | None = None
    estacionamento_id: str | None = None


# --- Schemas de Finanças ---
class ConfiguracaoPrecoBase(BaseModel):
    tipo_vaga: str
    valor_hora: float = Field(..., ge=0)
    valor_diaria: float | None = Field(None, ge=0)
    tolerancia_minutos: int = 15


class ConfiguracaoPrecoCreate(ConfiguracaoPrecoBase):
    estacionamento_id: str


class ConfiguracaoPrecoResponse(ConfiguracaoPrecoBase):
    id: str
    estacionamento_id: str
    criado_em: datetime
    # RF-60: expõe fração/minimo. A COLUNA nasceu com acento (valor_fração_15min);
    # a API devolve o nome limpo — validation_alias lê o ORM, serialization_alias
    # vale porque o FastAPI serializa response_model com by_alias=True.
    valor_fracao_15min: float | None = Field(
        None, validation_alias="valor_fração_15min", serialization_alias="valor_fracao_15min"
    )
    cobrar_valor_minimo: bool = True
    valor_minimo: float | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class ResumoFinanceiroResponse(BaseModel):
    estacionamento_id: str | None = None
    estacionamento_nome: str | None = None
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
    faturamento_por_dia: list[dict]
    faturamento_por_tipo_vaga: list[dict]



# --- Schemas do Módulo de Pagamentos ---
class CalcularTarifaRequest(BaseModel):
    cupom_codigo: str | None = None

class PagamentoRequest(BaseModel):
    historico_id: str
    metodo_pagamento: str = Field(..., pattern="^(pix|cartao_credito|cartao_debito|dinheiro)$")
    valor_recebido: float | None = None
    observacoes: str | None = None

class PagamentoResponse(BaseModel):
    id: str
    valor_total: float
    metodo_pagamento: str
    status_pagamento: str
    copia_cola_pix: str | None = None
    qr_code_pix: str | None = None
    link_pagamento: str | None = None
    data_pagamento: datetime | None = None
    troco: float | None = 0.0

    model_config = {"from_attributes": True}

class TarifaResponse(BaseModel):
    historico_id: str
    tempo_permanencia_minutos: int
    valor_bruto: float
    desconto_aplicado: float
    valor_total: float
    cupom_aplicado: str | None = None

class CupomCreate(BaseModel):
    estacionamento_id: str
    codigo: str
    tipo_desconto: str = Field(..., pattern="^(porcentagem|valor_fixo|isencao_total)$")
    valor_desconto: float = Field(..., ge=0)
    descricao: str | None = None
    limite_usos: int | None = None
    data_validade: datetime | None = None

class CupomResponse(BaseModel):
    id: str
    codigo: str
    tipo_desconto: str
    valor_desconto: float
    descricao: str | None
    limite_usos: int | None
    usos_realizados: int
    data_validade: datetime | None
    ativo: bool

    model_config = {"from_attributes": True}

class AbrirCaixaRequest(BaseModel):
    estacionamento_id: str
    valor_inicial: float = 0.0

class FecharCaixaRequest(BaseModel):
    valor_sangria: float = 0.0
    observacoes: str | None = None

class FechamentoCaixaResponse(BaseModel):
    id: str
    data_abertura: datetime
    data_fechamento: datetime | None
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
