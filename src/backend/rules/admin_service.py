from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.security import criar_hash_senha
from models.db_models import (
    Estacionamento, Andar, Vaga, Usuario,
    StatusVaga, TipoUsuario
)
from models.schemas import EstacionamentoCreate, AndarCreate, VagaCreate, UsuarioAdminCreate, UsuarioAdminUpdate


# --- Gerenciamento de Usuários ---
def criar_usuario_admin(db: Session, dados: UsuarioAdminCreate) -> Usuario:
    """Cria um novo usuário com cargo específico (apenas admin global)"""
    usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado no sistema"
        )

    # Valida role
    roles_validos = [r.value for r in TipoUsuario]
    if dados.role not in roles_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de usuário inválido. Valores aceitos: {', '.join(roles_validos)}"
        )

    # Se for gestor/financeiro, exige estacionamento vinculado
    if dados.role in [TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value] and not dados.estacionamento_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gestores e usuários de finanças devem estar vinculados a um estacionamento"
        )

    # Verifica se estacionamento existe se for informado
    if dados.estacionamento_id:
        est = db.query(Estacionamento).filter(Estacionamento.id == dados.estacionamento_id).first()
        if not est:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estacionamento não encontrado"
            )

    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        telefone=dados.telefone,
        placa_veiculo=dados.placa_veiculo,
        senha_hash=criar_hash_senha(dados.senha),
        role=dados.role,
        estacionamento_id=dados.estacionamento_id,
        is_ativo=True
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


def atualizar_usuario_admin(db: Session, usuario_id: str, dados: UsuarioAdminUpdate) -> Usuario:
    """Atualiza dados de qualquer usuário (apenas admin global)"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    dados_dict = dados.model_dump(exclude_unset=True)

    # Valida role se estiver sendo alterada
    if "role" in dados_dict:
        roles_validos = [r.value for r in TipoUsuario]
        if dados_dict["role"] not in roles_validos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de usuário inválido. Valores aceitos: {', '.join(roles_validos)}"
            )

        # Se for alterar para gestor/financeiro, garante estacionamento
        if dados_dict["role"] in [TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value]:
            if not dados_dict.get("estacionamento_id") and not usuario.estacionamento_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Gestores e usuários de finanças devem estar vinculados a um estacionamento"
                )

    if "estacionamento_id" in dados_dict and dados_dict["estacionamento_id"]:
        est = db.query(Estacionamento).filter(Estacionamento.id == dados_dict["estacionamento_id"]).first()
        if not est:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estacionamento não encontrado"
            )

    for campo, valor in dados_dict.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario


def listar_todos_usuarios(db: Session) -> List[Usuario]:
    """Lista todos os usuários do sistema (apenas admin)"""
    return db.query(Usuario).all()


def alternar_status_usuario(db: Session, usuario_id: str) -> Usuario:
    """Ativa/desativa um usuário"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    if usuario.role == TipoUsuario.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível desativar um administrador"
        )

    usuario.is_ativo = not usuario.is_ativo
    db.commit()
    db.refresh(usuario)
    return usuario


def promover_usuario_admin(db: Session, usuario_id: str) -> Usuario:
    """Promove um usuário para administrador"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    usuario.role = TipoUsuario.ADMIN.value
    usuario.estacionamento_id = None
    db.commit()
    db.refresh(usuario)
    return usuario


# --- Gerenciamento de Estacionamentos ---
def criar_estacionamento(db: Session, dados: EstacionamentoCreate) -> Estacionamento:
    """Cria um novo estacionamento (apenas admin)"""
    novo_est = Estacionamento(**dados.model_dump())
    db.add(novo_est)
    db.commit()
    db.refresh(novo_est)
    return novo_est


def atualizar_estacionamento(
    db: Session,
    estacionamento_id: str,
    dados: dict
) -> Estacionamento:
    """Atualiza dados de um estacionamento existente"""
    est = db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estacionamento não encontrado"
        )

    for campo, valor in dados.items():
        if valor is not None and hasattr(est, campo):
            setattr(est, campo, valor)

    db.commit()
    db.refresh(est)
    return est


def deletar_estacionamento(db: Session, estacionamento_id: str):
    """Remove um estacionamento (cascata apaga andares e vagas automaticamente)"""
    est = db.query(Estacionamento).filter(Estacionamento.id == estacionamento_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estacionamento não encontrado"
        )

    db.delete(est)
    db.commit()
    return {"mensagem": "Estacionamento removido com sucesso"}


# --- Gerenciamento de Andares ---
def criar_andar(db: Session, dados: AndarCreate) -> Andar:
    """Adiciona um novo andar a um estacionamento"""
    est = db.query(Estacionamento).filter(Estacionamento.id == dados.estacionamento_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estacionamento não encontrado"
        )

    novo_andar = Andar(**dados.model_dump())
    db.add(novo_andar)
    db.commit()
    db.refresh(novo_andar)
    return novo_andar


def deletar_andar(db: Session, andar_id: str):
    """Remove um andar e todas as suas vagas"""
    andar = db.query(Andar).filter(Andar.id == andar_id).first()
    if not andar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Andar não encontrado"
        )

    db.delete(andar)
    db.commit()
    return {"mensagem": "Andar removido com sucesso"}


# --- Gerenciamento de Vagas ---
def criar_vaga(db: Session, dados: VagaCreate) -> Vaga:
    """Cria uma nova vaga em um andar"""
    andar = db.query(Andar).filter(Andar.id == dados.andar_id).first()
    if not andar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Andar não encontrado"
        )

    nova_vaga = Vaga(**dados.model_dump())
    db.add(nova_vaga)
    db.commit()
    db.refresh(nova_vaga)
    return nova_vaga


def criar_vagas_em_lote(db: Session, andar_id: str, quantidade: int, prefixo_codigo: str = "") -> List[Vaga]:
    """Cria várias vagas de uma vez em um andar (útil para cadastro rápido)"""
    andar = db.query(Andar).filter(Andar.id == andar_id).first()
    if not andar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Andar não encontrado"
        )

    vagas_existentes = db.query(Vaga).filter(Vaga.andar_id == andar_id).count()
    novas_vagas = []

    for i in range(quantidade):
        numero = vagas_existentes + i + 1
        codigo = f"{prefixo_codigo}{numero:02d}"
        vaga = Vaga(
            andar_id=andar_id,
            codigo=codigo,
            status=StatusVaga.LIVRE
        )
        db.add(vaga)
        novas_vagas.append(vaga)

    db.commit()
    for v in novas_vagas:
        db.refresh(v)
    return novas_vagas


def deletar_vaga(db: Session, vaga_id: str):
    """Remove uma vaga"""
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada"
        )

    db.delete(vaga)
    db.commit()
    return {"mensagem": "Vaga removida com sucesso"}
