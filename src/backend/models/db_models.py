import uuid
import enum
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class StatusVaga(str, enum.Enum):
    """Enum padronizado de status de vaga"""
    LIVRE = "livre"
    OCUPADA = "ocupada"
    RESERVADA = "reservada"
    INATIVA = "inativa"


class StatusReserva(str, enum.Enum):
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    CONCLUIDA = "concluida"


class TipoVaga(str, enum.Enum):
    COMUM = "comum"
    IDOSO = "idoso"
    PCD = "pcd"
    MOTO = "moto"
    ELETRICO = "eletrico"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    senha_hash = Column(String, nullable=False)
    placa_veiculo = Column(String, nullable=True, index=True)
    telefone = Column(String, nullable=True)
    is_ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    reservas = relationship("Reserva", back_populates="usuario", cascade="all, delete-orphan")
    historicos = relationship("Historico", back_populates="usuario")


class Estacionamento(Base):
    __tablename__ = "estacionamentos"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    nome = Column(String, nullable=False, index=True)
    endereco = Column(String, nullable=True)
    total_andares = Column(Integer, nullable=False, default=1)
    total_vagas = Column(Integer, nullable=False, default=0)
    hora_abertura = Column(String, default="06:00")
    hora_fechamento = Column(String, default="22:00")
    taxa_hora = Column(Float, default=0.0)
    telefone = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    andares = relationship(
        "Andar",
        back_populates="estacionamento",
        cascade="all, delete-orphan",
        order_by="Andar.numero_andar"
    )
    historicos = relationship("Historico", back_populates="estacionamento")


class Andar(Base):
    __tablename__ = "andares"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    estacionamento_id = Column(
        String,
        ForeignKey("estacionamentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    numero_andar = Column(Integer, nullable=False)
    capacidade = Column(Integer, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    estacionamento = relationship("Estacionamento", back_populates="andares")
    vagas = relationship("Vaga", back_populates="andar", cascade="all, delete-orphan")


class Vaga(Base):
    __tablename__ = "vagas"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    andar_id = Column(
        String,
        ForeignKey("andares.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    codigo = Column(String, nullable=False, index=True)  # Ex: A1, B12, C03
    tipo = Column(String, nullable=False, default=TipoVaga.COMUM)
    posicao_x = Column(Integer, nullable=True)  # Posição para mapa
    posicao_y = Column(Integer, nullable=True)
    # Status da vaga: 'livre', 'ocupada', 'reservada', 'inativa'
    status = Column(String, nullable=False, default=StatusVaga.LIVRE, index=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    ultima_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    andar = relationship("Andar", back_populates="vagas")
    reservas = relationship("Reserva", back_populates="vaga")
    historicos = relationship("Historico", back_populates="vaga")


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    usuario_id = Column(
        String,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    vaga_id = Column(
        String,
        ForeignKey("vagas.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    horario_inicio = Column(DateTime(timezone=True), nullable=False)
    horario_fim = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default=StatusReserva.CONFIRMADA, index=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    usuario = relationship("Usuario", back_populates="reservas")
    vaga = relationship("Vaga", back_populates="reservas")


class Historico(Base):
    """Tabela de histórico de entradas/saídas para relatórios"""
    __tablename__ = "historicos"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    usuario_id = Column(String, ForeignKey("usuarios.id"), nullable=True)
    estacionamento_id = Column(
        String,
        ForeignKey("estacionamentos.id"),
        nullable=False,
        index=True
    )
    vaga_id = Column(
        String,
        ForeignKey("vagas.id"),
        nullable=False,
        index=True
    )
    placa_veiculo = Column(String, index=True)
    entrada_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    saida_em = Column(DateTime(timezone=True), nullable=True)
    tempo_permanencia_minutos = Column(Integer, nullable=True)
    valor_total = Column(Float, nullable=True)

    # Relacionamentos
    usuario = relationship("Usuario", back_populates="historicos")
    estacionamento = relationship("Estacionamento", back_populates="historicos")
    vaga = relationship("Vaga", back_populates="historicos")
