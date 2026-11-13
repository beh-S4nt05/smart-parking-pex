"""Escopo de estacionamentos — FONTE ÚNICA de verdade (tenant isolation).

Regras de negócio consolidadas:

* **Admin global**: vê/age em todos os shoppings (``None`` = sem restrição).
* **Gestor**: pode ser vinculado a VÁRIOS shoppings (``usuario_estacionamentos``).
  Só enxerga e opera nesse conjunto. Pedir o de outro gestor => 403.
* **Financeiro**: exatamente UM shopping (o principal). Além disso o serviço
  de usuários garante no máximo UMA conta financeira por shopping.
* **Motorista / anônimo**: sem escopo de painel — continuam usando apenas as
  rotas públicas de vitrine, sem dados gerenciais.

Antes havia duas implementações divergentes (``core/deps.py`` e
``api/api.py::garantir_escopo_relatorio``) e nenhuma delas conhecia vínculos
múltiplos. Todas as rotas agora delegam a este módulo.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.db_models import Andar, TipoUsuario, Usuario, Vaga

PAPEIS_PAINEL = (TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value)


def ids_permitidos(usuario: Usuario) -> set[str] | None:
    """Retorna os ids permitidos, ou ``None`` para admin global (todos).

    Para papéis fora do painel retorna ``None`` também — eles nunca chegam
    aqui pelas rotas gerenciais (bloqueadas por ``permissao_necessaria``), e
    nas rotas públicas o chamador decide o que fazer.
    """
    if usuario.role == TipoUsuario.ADMIN.value:
        return None
    if usuario.role not in PAPEIS_PAINEL:
        return set()

    ids = set(usuario.estacionamento_ids)  # principal + vínculos N:N
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não está vinculado a nenhum shopping. Contate o administrador.",
        )
    if usuario.role == TipoUsuario.FINANCEIRO.value:
        # 1:1 por definição — ignora vínculos extras que possam existir em
        # bases antigas, em vez de conceder acesso indevido.
        principal = usuario.estacionamento_id or sorted(ids)[0]
        return {principal}
    return ids


def garantir_escopo_estacionamento(
    usuario: Usuario,
    estacionamento_id: str | None,
    acao: str = "usar este shopping",
) -> str | None:
    """Valida UM shopping e devolve o id a ser usado (nunca o id alheio).

    Admin: devolve o id pedido ou ``None`` (agregado global).
    Gestor/financeiro: id alheio => 403; sem id => principal (nunca "todos").
    """
    permitidos = ids_permitidos(usuario)
    if permitidos is None:  # admin global
        return estacionamento_id
    if not permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você não tem permissão para esta operação.",
        )
    if estacionamento_id:
        if estacionamento_id not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Você só pode {acao} nos seus shoppings.",
            )
        return estacionamento_id
    # Sem seleção explícita: nunca devolver "todos" para papel escopado.
    return usuario.estacionamento_id or sorted(permitidos)[0]


def garantir_vagas_no_escopo(db: Session, usuario: Usuario, vaga_ids: list[str]) -> None:
    """Bloqueia PATCH de vagas que não pertençam a NENHUM shopping permitido."""
    if usuario.role == TipoUsuario.ADMIN.value:
        return
    permitidos = ids_permitidos(usuario)
    if not permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não está vinculado a nenhum shopping.",
        )
    fora = (
        db.query(Vaga.id)
        .join(Andar, Vaga.andar_id == Andar.id)
        .filter(Vaga.id.in_(vaga_ids), Andar.estacionamento_id.not_in(permitidos))
        .count()
    )
    if fora:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Uma ou mais vagas não pertencem aos seus shoppings.",
        )


def garantir_leitura_publica_no_escopo(
    usuario: Usuario | None, estacionamento_id: str
) -> None:
    """Fecha o BOLA nas rotas públicas de mapa/vagas para papéis de painel.

    Anônimo, motorista e admin seguem com a vitrine pública intacta. Um gestor
    ou financeiro AUTENTICADO não pode pedir o mapa de shopping alheio — a UI
    já não lista, e agora a API também não entrega.
    """
    if usuario is None or usuario.role not in PAPEIS_PAINEL:
        return
    permitidos = ids_permitidos(usuario)
    if estacionamento_id not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Este shopping não está vinculado à sua conta.",
        )


def filtrar_estacionamentos(db: Session, usuario: Usuario | None):
    """Lista de shoppings que ``usuario`` pode ver.

    ``None`` (anônimo/motorista) e admin recebem a vitrine completa: a Home é
    pública por design. Gestor/financeiro logados recebem SOMENTE o seu escopo
    — inclusive na vitrine, para não haver "acesso a outro shopping" via API.
    """
    from models.db_models import Estacionamento

    query = db.query(Estacionamento)
    if usuario is None or usuario.role == TipoUsuario.ADMIN.value:
        return query.all()
    if usuario.role not in PAPEIS_PAINEL:
        return query.all()  # motorista: vitrine pública normal
    permitidos = ids_permitidos(usuario)
    return query.filter(Estacionamento.id.in_(permitidos)).all()
