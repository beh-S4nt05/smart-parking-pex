from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from .database import Base  # Importa a instância declarativa base do database.py


class Estacionamento(Base):
    __tablename__ = "estacionamentos"
    id = Column(String, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    endereco = Column(String)
    total_andares = Column(Integer)
    total_vagas = Column(Integer)


class Vaga(Base):
    __tablename__ = "vagas"
    id = Column(String, primary_key=True, index=True)
    andar_id = Column(String, ForeignKey("andares.id"))
    codigo = Column(String, nullable=False)  # Ex: A1, B12 [14]
    status = Column(String, default="livre")  # livre, ocupada, reservada, inativa

