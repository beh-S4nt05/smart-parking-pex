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


class TipoUsuario(str, enum.Enum):
    """Níveis de permissão do sistema"""
    PUBLICO = "publico"
    USUARIO = "usuario"
    FINANCEIRO = "financeiro"
    GESTOR = "gestor"
    ADMIN = "admin"


class TipoDesconto(str, enum.Enum):
    PORCENTAGEM = "porcentagem"
    VALOR_FIXO = "valor_fixo"
    ISENCAO_TOTAL = "isencao_total"


class StatusPagamento(str, enum.Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    PAGO = "pago"
    CANCELADO = "cancelado"
    ESTORNADO = "estornado"


class MetodoPagamento(str, enum.Enum):
    PIX = "pix"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    DINHEIRO = "dinheiro"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    senha_hash = Column(String, nullable=False)
    placa_veiculo = Column(String, nullable=True, index=True)
    telefone = Column(String, nullable=True)
    is_ativo = Column(Boolean, default=True)
    role = Column(String, nullable=False, default=TipoUsuario.USUARIO, index=True)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id"), nullable=True, index=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    reservas = relationship("Reserva", back_populates="usuario", cascade="all, delete-orphan")
    historicos = relationship("Historico", back_populates="usuario", foreign_keys="Historico.usuario_id")
    estacionamento_gerenciado = relationship("Estacionamento")
    fechamentos_caixa_abertos = relationship("FechamentoCaixa", back_populates="usuario_abertura", foreign_keys="FechamentoCaixa.usuario_abertura_id")
    fechamentos_caixa = relationship("FechamentoCaixa", back_populates="usuario_fechamento", foreign_keys="FechamentoCaixa.usuario_fechamento_id")


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

    andares = relationship("Andar", back_populates="estacionamento", cascade="all, delete-orphan", order_by="Andar.numero_andar")
    historicos = relationship("Historico", back_populates="estacionamento", foreign_keys="Historico.estacionamento_id")
    configuracoes_precos = relationship("ConfiguracaoPreco", back_populates="estacionamento", cascade="all, delete-orphan")
    cupons = relationship("CupomDesconto", back_populates="estacionamento", cascade="all, delete-orphan")
    fechamentos_caixa = relationship("FechamentoCaixa", back_populates="estacionamento", cascade="all, delete-orphan")


class Andar(Base):
    __tablename__ = "andares"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_andar = Column(Integer, nullable=False)
    capacidade = Column(Integer, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    estacionamento = relationship("Estacionamento", back_populates="andares")
    vagas = relationship("Vaga", back_populates="andar", cascade="all, delete-orphan")


class Vaga(Base):
    __tablename__ = "vagas"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    andar_id = Column(String, ForeignKey("andares.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String, nullable=False, index=True)
    tipo = Column(String, nullable=False, default=TipoVaga.COMUM)
    posicao_x = Column(Integer, nullable=True)
    posicao_y = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default=StatusVaga.LIVRE, index=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    ultima_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    andar = relationship("Andar", back_populates="vagas")
    reservas = relationship("Reserva", back_populates="vaga")
    historicos = relationship("Historico", back_populates="vaga")


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    usuario_id = Column(String, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    vaga_id = Column(String, ForeignKey("vagas.id", ondelete="CASCADE"), nullable=False, index=True)
    horario_inicio = Column(DateTime(timezone=True), nullable=False)
    horario_fim = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default=StatusReserva.CONFIRMADA, index=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="reservas")
    vaga = relationship("Vaga", back_populates="reservas")


class ConfiguracaoPreco(Base):
    __tablename__ = "configuracoes_precos"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_vaga = Column(String, nullable=False)
    valor_hora = Column(Float, nullable=False)
    valor_fração_15min = Column(Float, nullable=True)
    valor_diaria = Column(Float, nullable=True)
    tolerancia_minutos = Column(Integer, default=15)
    cobrar_valor_minimo = Column(Boolean, default=True)
    valor_minimo = Column(Float, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    estacionamento = relationship("Estacionamento", back_populates="configuracoes_precos")


class Historico(Base):
    __tablename__ = "historicos"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    usuario_id = Column(String, ForeignKey("usuarios.id"), nullable=True)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id"), nullable=False, index=True)
    vaga_id = Column(String, ForeignKey("vagas.id"), nullable=False, index=True)
    placa_veiculo = Column(String, index=True, nullable=True)
    entrada_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    saida_em = Column(DateTime(timezone=True), nullable=True)
    tempo_permanencia_minutos = Column(Integer, nullable=True)
    valor_bruto = Column(Float, nullable=True)
    valor_desconto = Column(Float, default=0.0)
    valor_total = Column(Float, nullable=True)
    cupom_aplicado = Column(String, nullable=True)
    status_pagamento = Column(String, nullable=False, default=StatusPagamento.PENDENTE)
    forma_pagamento = Column(String, nullable=True)
    pagamento_id = Column(String, ForeignKey("pagamentos.id"), nullable=True)
    comprovante_url = Column(String, nullable=True)
    is_saida_manual = Column(Boolean, default=False)
    observacoes = Column(Text, nullable=True)

    usuario = relationship("Usuario", back_populates="historicos", foreign_keys=[usuario_id])
    estacionamento = relationship("Estacionamento", back_populates="historicos", foreign_keys=[estacionamento_id])
    vaga = relationship("Vaga", back_populates="historicos", foreign_keys=[vaga_id])
    pagamento = relationship("Pagamento", foreign_keys=[pagamento_id])


class CupomDesconto(Base):
    __tablename__ = "cupons_desconto"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id"), nullable=False, index=True)
    codigo = Column(String, nullable=False, unique=True, index=True)
    tipo_desconto = Column(String, nullable=False)
    valor_desconto = Column(Float, nullable=False)
    descricao = Column(String, nullable=True)
    limite_usos = Column(Integer, nullable=True)
    usos_realizados = Column(Integer, default=0)
    data_validade = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    estacionamento = relationship("Estacionamento", back_populates="cupons")


class FechamentoCaixa(Base):
    __tablename__ = "fechamentos_caixa"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id"), nullable=False, index=True)
    usuario_abertura_id = Column(String, ForeignKey("usuarios.id"), nullable=False)
    usuario_fechamento_id = Column(String, ForeignKey("usuarios.id"), nullable=True)
    data_abertura = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    data_fechamento = Column(DateTime(timezone=True), nullable=True)
    valor_inicial_caixa = Column(Float, default=0.0)
    valor_pix = Column(Float, default=0.0)
    valor_cartao_credito = Column(Float, default=0.0)
    valor_cartao_debito = Column(Float, default=0.0)
    valor_dinheiro = Column(Float, default=0.0)
    valor_total = Column(Float, default=0.0)
    quantidade_pagamentos = Column(Integer, default=0)
    valor_descontos = Column(Float, default=0.0)
    valor_sangria = Column(Float, default=0.0)
    observacoes = Column(Text, nullable=True)
    fechado = Column(Boolean, default=False)

    estacionamento = relationship("Estacionamento", back_populates="fechamentos_caixa", foreign_keys=[estacionamento_id])
    usuario_abertura = relationship("Usuario", foreign_keys=[usuario_abertura_id])
    usuario_fechamento = relationship("Usuario", foreign_keys=[usuario_fechamento_id], back_populates="fechamentos_caixa")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    historico_id = Column(String, ForeignKey("historicos.id"), nullable=False)
    estacionamento_id = Column(String, ForeignKey("estacionamentos.id"), nullable=False, index=True)
    usuario_id = Column(String, ForeignKey("usuarios.id"), nullable=True)
    valor_bruto = Column(Float, nullable=False)
    valor_desconto = Column(Float, default=0.0)
    valor_total = Column(Float, nullable=False)
    metodo_pagamento = Column(String, nullable=False)
    status_pagamento = Column(String, nullable=False, default=StatusPagamento.PENDENTE, index=True)
    gateway_pagamento = Column(String, nullable=True)
    id_transacao_gateway = Column(String, nullable=True)
    qr_code_pix = Column(Text, nullable=True)
    copia_cola_pix = Column(Text, nullable=True)
    link_pagamento = Column(Text, nullable=True)
    data_pagamento = Column(DateTime(timezone=True), nullable=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_cancelamento = Column(DateTime(timezone=True), nullable=True)
    observacoes = Column(Text, nullable=True)


    estacionamento = relationship("Estacionamento", foreign_keys=[estacionamento_id])
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
