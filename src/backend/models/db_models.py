# db_models.py
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    senha_hash = Column(String, nullable=False)
    placa_veiculo = Column(String, nullable=True, index=True) # Indexado para buscas rápidas de entrada/saída
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
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    andares = relationship("Andar", back_populates="estacionamento", cascade="all, delete-orphan", order_by="Andar.numero_andar")


class Andar(Base):
    __tablename__ = "andares"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_andar = Column(Integer, nullable=False) # Ex: 0 (Térreo), 1, 2...
    capacidade = Column(Integer, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    estacionamento = relationship("Estacionamento", back_populates="andares")
    vagas = relationship("Vaga", back_populates="andar", cascade="all, delete-orphan")


class Vaga(Base):
    __tablename__ = "vagas"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    andar_id = Column(String, ForeignKey("andares.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String, nullable=False, index=True) # Ex: A1, B12, C03
    
    # Status da vaga: 'livre', 'ocupada', 'reservada', 'inativa'
    status = Column(String, nullable=False, default="livre", index=True)
    
    # Tipo de veículo suportado: 'carro', 'moto', 'caminhonete'
    tipo_veiculo = Column(String, nullable=False, default="carro", index=True)
    
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    andar = relationship("Andar", back_populates="vagas")
    reservas = relationship("Reserva", back_populates="vaga", cascade="all, delete-orphan")
    historicos = relationship("Historico", back_populates="vaga")


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    vaga_id = Column(String, ForeignKey("vagas.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(String, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    
    dt_inicio = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    dt_expiracao = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Status do fluxo: 'ativa' (em andamento), 'concluida' (usuário estacionou), 'cancelada' (pelo usuário), 'expirada' (tempo limite excedido)
    status = Column(String, nullable=False, default="ativa", index=True)
    
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    vaga = relationship("Vaga", back_populates="reservas")
    usuario = relationship("Usuario", back_populates="reservas")


class Historico(Base):
    __tablename__ = "historicos"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    vaga_id = Column(String, ForeignKey("vagas.id", ondelete="SET NULL"), nullable=True, index=True) # SET NULL garante integridade se vaga for deletada
    usuario_id = Column(String, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    
    placa_veiculo = Column(String, nullable=False, index=True)
    dt_entrada = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    dt_saida = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Origem do fluxo de entrada: 'reserva' ou 'entrada_direta'
    origem = Column(String, nullable=False, default="entrada_direta", index=True)
    
    # Métricas de escalabilidade/permanência adicionais
    tempo_permanencia_minutos = Column(Integer, nullable=True) # Calculado no checkout para relatórios rápidos

    # Relacionamentos
    vaga = relationship("Vaga", back_populates="historicos")
    usuario = relationship("Usuario", back_populates="historicos")
