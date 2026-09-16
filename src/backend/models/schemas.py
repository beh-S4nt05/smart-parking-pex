# schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- ENUMS PARA CONTROLE DE FLUXO ---

class VagaStatusEnum(str, Enum):
    LIVRE = "livre"
    OCUPADA = "ocupada"
    RESERVADA = "reservada"
    INATIVA = "inativa"

class TipoVeiculoEnum(str, Enum):
    CARRO = "carro"
    MOTO = "moto"
    CAMINHONETE = "caminhonete"

class ReservaStatusEnum(str, Enum):
    ATIVA = "ativa"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
    EXPIRADA = "expirada"

class OrigemEntradaEnum(str, Enum):
    RESERVA = "reserva"
    ENTRADA_DIRETA = "entrada_direta"


# --- SCHEMAS DE USUÁRIO ---

class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    placa_veiculo: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6, description="Senha do usuário com no mínimo 6 caracteres")

class UsuarioResponse(UsuarioBase):
    id: str
    criado_em: datetime

    class Config:
        from_attributes = True


# --- SCHEMAS DE ESTACIONAMENTO ---

class EstacionamentoBase(BaseModel):
    nome: str
    endereco: Optional[str] = None
    total_andares: int = Field(default=1, ge=1)
    total_vagas: int = Field(default=0, ge=0)

class EstacionamentoCreate(EstacionamentoBase):
    pass

class EstacionamentoResponse(EstacionamentoBase):
    id: str
    criado_em: datetime

    class Config:
        from_attributes = True


# --- SCHEMAS DE ANDAR ---

class AndarBase(BaseModel):
    numero_andares: int = Field(..., alias="numero_andar")
    capacidade: int = Field(..., ge=1)

    class Config:
        populate_by_name = True

class AndarCreate(AndarBase):
    estacionamento_id: str

class AndarResponse(AndarBase):
    id: str
    estacionamento_id: str
    criado_em: datetime

    class Config:
        from_attributes = True


# --- SCHEMAS DE VAGA ---

class VagaBase(BaseModel):
    codigo: str
    status: VagaStatusEnum = VagaStatusEnum.LIVRE
    tipo_veiculo: TipoVeiculoEnum = TipoVeiculoEnum.CARRO

class VagaCreate(VagaBase):
    andar_id: str

class VagaUpdateStatus(BaseModel):
    status: VagaStatusEnum

class VagaResponse(VagaBase):
    id: str
    andar_id: str
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- SCHEMAS DE RESERVA ---

class ReservaBase(BaseModel):
    vaga_id: str
    usuario_id: str
    dt_expiracao: datetime
    status: ReservaStatusEnum = ReservaStatusEnum.ATIVA

class ReservaCreate(BaseModel):
    vaga_id: str
    usuario_id: str
    minutos_tolerancia: int = Field(default=15, ge=5, le=60, description="Minutos até a reserva expirar automaticamente")

class ReservaUpdateStatus(BaseModel):
    status: ReservaStatusEnum

class ReservaResponse(ReservaBase):
    id: str
    dt_inicio: datetime
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- SCHEMAS DE HISTÓRICO ---

class HistoricoBase(BaseModel):
    vaga_id: Optional[str] = None
    usuario_id: Optional[str] = None
    placa_veiculo: str
    origem: OrigemEntradaEnum = OrigemEntradaEnum.ENTRADA_DIRETA

class HistoricoCreate(HistoricoBase):
    pass

class HistoricoCheckout(BaseModel):
    dt_saida: Optional[datetime] = None

class HistoricoResponse(HistoricoBase):
    id: str
    dt_entrada: datetime
    dt_saida: Optional[datetime] = None
    tempo_permanencia_minutos: Optional[int] = None

    class Config:
        from_attributes = True
