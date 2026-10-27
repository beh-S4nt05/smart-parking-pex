
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.security import criar_hash_senha
from models.db_models import (
    Andar,
    Estacionamento,
    FechamentoCaixa,
    Historico,
    Pagamento,
    Reserva,
    Sensor,
    SensorEvento,
    StatusVaga,
    TipoUsuario,
    TipoVaga,
    Usuario,
    Vaga,
)
from models.schemas import (
    AndarCreate,
    EstacionamentoCreate,
    UsuarioAdminCreate,
    UsuarioAdminUpdate,
    VagaCreate,
)


# --- Purga operacional compartilhada pelos "deletar_*" ---
def _purgar_operacional(db: Session, estacionamento_id: str | None = None,
                        vaga_ids: list[str] | None = None) -> None:
    """
    Apaga na ordem certa os dados OPERACIONAIS (pagamentos → históricos →
    reservas) antes de deletar estacionamento/andar/vaga.

    Por que isso existe: os FKs de `historicos`/`reservas`/`pagamentos` são
    NOT NULL e SEM `ondelete` — o comportamento padrão do SQLAlchemy ao
    deletar o pai é SET NULL nos filhos, e isso arrebenta o constraint
    (500 IntegrityError no DELETE com qualquer histórico gravado). A
    auditoria de 20/10 pegou isso ao deletar um estacionamento que tinha 1
    transição de vaga. Aqui usamos DELETE em massa (não ORM), então o que
    sobra (vagas→andares→config/cupom/fechamento) continua fluindo pelo
    cascade delete-orphan já configurado nos relacionamentos.
    """
    if estacionamento_id is not None:
        vaga_ids = [
            vid for (vid,) in
            db.query(Vaga.id)
            .join(Andar, Vaga.andar_id == Andar.id)
            .filter(Andar.estacionamento_id == estacionamento_id)
        ]
        # ORDEM importada (auditoria 22/10-n): em Postgres o FK
        # historicos.pagamento_id é RESTRICT — apagar os pagamentos ANTES de
        # soltar a referência derrubava o DELETE com 500. Primeiro NULL-out.
        db.query(Historico).filter(
            Historico.estacionamento_id == estacionamento_id,
            Historico.pagamento_id.isnot(None),
        ).update({Historico.pagamento_id: None}, synchronize_session=False)
        db.query(Pagamento).filter(Pagamento.estacionamento_id == estacionamento_id).delete(synchronize_session=False)
        db.query(Historico).filter(Historico.estacionamento_id == estacionamento_id).delete(synchronize_session=False)
        # caixa: o cascade do ORM cobriria, mas deletamos ANTES de mexer nos
        # usuários que abriram os caixas (FK RESTRICT em usuarios.id)
        db.query(FechamentoCaixa).filter(
            FechamentoCaixa.estacionamento_id == estacionamento_id
        ).delete(synchronize_session=False)
        # dispositivos de medição do estacionamento (tabela nova de 22/10 —
        # sem relationship no ORM; sem isto sobrariam linhas órfãs/403)
        sensores_ids = [sid for (sid,) in db.query(Sensor.id).filter(Sensor.estacionamento_id == estacionamento_id)]
        if sensores_ids:
            db.query(SensorEvento).filter(SensorEvento.sensor_id.in_(sensores_ids)).delete(synchronize_session=False)
            db.query(Sensor).filter(Sensor.id.in_(sensores_ids)).delete(synchronize_session=False)
        # gestores/financeiros vinculados: ficam órfãos (SQLite) ou travam o
        # DELETE (Postgres, FK RESTRICT) — a conta só existe PARA a filial.
        vinculados = [
            uid for (uid,) in db.query(Usuario.id).filter(
                Usuario.estacionamento_id == estacionamento_id,
                Usuario.role.in_([TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value]),
            )
        ]
        if vinculados:
            db.query(Reserva).filter(Reserva.usuario_id.in_(vinculados)).delete(synchronize_session=False)
            db.query(Pagamento).filter(Pagamento.usuario_id.in_(vinculados)).update(
                {Pagamento.usuario_id: None}, synchronize_session=False
            )
            db.query(Usuario).filter(Usuario.id.in_(vinculados)).delete(synchronize_session=False)
        # sessões QR do simulador apontando para a filial morta (estado em
        # memória — revogar explicitamente, senão o QR vive sem dono)
        from rules import simulador_service
        simulador_service.revogar_por_estacionamento(estacionamento_id)
    if vaga_ids:
        # pagamentos ATRAVÉS dos históricos destas vagas também (cobre o DELETE
        # de andar/vaga isolado, onde o branch de estacionamento não rodou)
        historicos_afetados = db.query(Historico.id).filter(Historico.vaga_id.in_(vaga_ids))
        db.query(Historico).filter(
            Historico.vaga_id.in_(vaga_ids), Historico.pagamento_id.isnot(None)
        ).update({Historico.pagamento_id: None}, synchronize_session=False)
        db.query(Pagamento).filter(Pagamento.historico_id.in_(historicos_afetados)).delete(synchronize_session=False)
        db.query(Historico).filter(Historico.vaga_id.in_(vaga_ids)).delete(synchronize_session=False)
        db.query(Reserva).filter(Reserva.vaga_id.in_(vaga_ids)).delete(synchronize_session=False)
        # log bruto de sensor perde a vaga (não a estadia): desanexa, preserva auditoria
        db.query(SensorEvento).filter(SensorEvento.vaga_id.in_(vaga_ids)).update(
            {SensorEvento.vaga_id: None}, synchronize_session=False
        )
    db.flush()


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

    # Guarda anti-lockout (22/10-n): o ÚLTIMO admin ativo não pode ser
    # rebaixado nem desativado — sem isto, um PUT malicioso/sem atenção
    # deixava o sistema sem ninguém capaz de gerenciar nada.
    perde_admin = (
        usuario.role == TipoUsuario.ADMIN.value
        and (
            ("role" in dados_dict and dados_dict["role"] != TipoUsuario.ADMIN.value)
            or dados_dict.get("is_ativo") is False
        )
    )
    if perde_admin:
        restantes = db.query(Usuario).filter(
            Usuario.role == TipoUsuario.ADMIN.value,
            Usuario.is_ativo.is_(True),
            Usuario.id != usuario.id,
        ).count()
        if restantes == 0:
            raise HTTPException(
                status_code=422,
                detail="Não é possível rebaixar/desativar o último administrador ativo do sistema",
            )

    # Valida role se estiver sendo alterada
    if "role" in dados_dict:
        roles_validos = [r.value for r in TipoUsuario]
        if dados_dict["role"] not in roles_validos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de usuário inválido. Valores aceitos: {', '.join(roles_validos)}"
            )

    # Valida o ESTADO FINAL, não apenas a transição: remover explicitamente o
    # vínculo de um gestor já existente também o deixaria sem acesso ao painel.
    role_final = dados_dict.get("role", usuario.role)
    estacionamento_final = dados_dict.get(
        "estacionamento_id", usuario.estacionamento_id
    )
    if (
        role_final in [TipoUsuario.GESTOR.value, TipoUsuario.FINANCEIRO.value]
        and not estacionamento_final
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gestores e usuários de finanças devem estar vinculados a um estacionamento"
        )

    if dados_dict.get("estacionamento_id"):
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


def listar_todos_usuarios(db: Session) -> list[Usuario]:
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

    _purgar_operacional(db, estacionamento_id=estacionamento_id)
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

    duplicado = db.query(Andar).filter(
        Andar.estacionamento_id == dados.estacionamento_id,
        Andar.numero_andar == dados.numero_andar,
    ).first()
    if duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O estacionamento já tem um andar {dados.numero_andar}",
        )

    novo_andar = Andar(**dados.model_dump())
    db.add(novo_andar)
    db.commit()
    db.refresh(novo_andar)
    return novo_andar


def atualizar_andar(db: Session, andar_id: str, dados: dict) -> Andar:
    """RF-32: renomeia número/ajusta capacidade de um andar."""
    andar = db.query(Andar).filter(Andar.id == andar_id).first()
    if not andar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Andar não encontrado")
    if "numero_andar" in dados and dados["numero_andar"] is not None:
        novo = int(dados["numero_andar"])
        colidiu = db.query(Andar).filter(
            Andar.estacionamento_id == andar.estacionamento_id,
            Andar.numero_andar == novo, Andar.id != andar_id,
        ).first()
        if colidiu:
            raise HTTPException(status_code=409, detail=f"O estacionamento já tem um andar {novo}")
        andar.numero_andar = novo
    if "capacidade" in dados and dados["capacidade"] is not None:
        cap = int(dados["capacidade"])
        reais = db.query(Vaga).filter(Vaga.andar_id == andar_id).count()
        if cap < reais:
            raise HTTPException(
                status_code=422,
                detail=f"Capacidade {cap} menor que as {reais} vagas já cadastradas no andar",
            )
        andar.capacidade = cap
    db.commit(); db.refresh(andar)
    return andar


def atualizar_vaga(db: Session, vaga_id: str, dados: dict) -> Vaga:
    """RF-33: edita código/tipo/posição de uma vaga (sem mexer no status)."""
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada")
    if dados.get("tipo"):
        if dados["tipo"] not in {t.value for t in TipoVaga}:
            raise HTTPException(status_code=422, detail="tipo inválido")
        vaga.tipo = dados["tipo"]
    if dados.get("codigo"):
        cod = str(dados["codigo"]).strip().upper()
        if not cod:
            raise HTTPException(status_code=422, detail="codigo vazio")
        dup = db.query(Vaga).filter(
            Vaga.andar_id == vaga.andar_id,
            func.upper(Vaga.codigo) == cod,
            Vaga.id != vaga_id,
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Já existe a vaga {cod} neste andar")
        vaga.codigo = cod
    for campo in ("posicao_x", "posicao_y"):
        if dados.get(campo) is not None:
            setattr(vaga, campo, int(dados[campo]))
    db.commit(); db.refresh(vaga)
    return vaga


def reset_senha_admin(db: Session, usuario_id: str) -> str:
    """
    RF-14 (sem SMTP no projeto): o admin gera uma senha temporária de balcão.
    A senha antiga morre junto com TODAS as sessões do usuário (revogação
    global) — quem tinha o app aberto é forçado a religar com a nova.
    """
    import secrets as _sec
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789abcdefghjkmnpqrstuvwxyz"
    temporaria = "".join(_sec.choice(alfabeto) for _ in range(10))
    usuario.senha_hash = criar_hash_senha(temporaria)
    from core.timeutils import utc_agora
    from models.db_models import RevogacaoToken
    db.add(RevogacaoToken(jti=None, usuario_id=usuario.id, motivo="reset_admin", criado_em=utc_agora()))
    db.commit()
    return temporaria


def deletar_andar(db: Session, andar_id: str):
    """Remove um andar e todas as suas vagas"""
    andar = db.query(Andar).filter(Andar.id == andar_id).first()
    if not andar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Andar não encontrado"
        )

    # same IntegrityError guard as deletar_estacionamento: histórico/reserva
    # apontando para as vagas deste andar precisam sair ANTES do andar
    _purgar_operacional(db, vaga_ids=[vid for (vid,) in db.query(Vaga.id).filter(Vaga.andar_id == andar_id)])
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

    payload = dados.model_dump()
    codigo = str(payload["codigo"]).strip().upper()
    if not codigo:
        raise HTTPException(status_code=422, detail="codigo vazio")
    payload["codigo"] = codigo
    duplicada = db.query(Vaga).filter(
        Vaga.andar_id == dados.andar_id,
        func.upper(Vaga.codigo) == codigo,
    ).first()
    if duplicada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe a vaga {codigo} neste andar",
        )

    nova_vaga = Vaga(**payload)
    db.add(nova_vaga)
    db.commit()
    db.refresh(nova_vaga)
    return nova_vaga


def criar_vagas_em_lote(
    db: Session,
    andar_id: str,
    quantidade: int,
    prefixo_codigo: str = "",
    tipo: str = TipoVaga.COMUM,
) -> list[Vaga]:
    """Cria várias vagas de uma vez em um andar (útil para cadastro rápido).

    ACH-17: o lote agora aceita `tipo` e mantém `andares.capacidade` e
    `estacionamentos.total_vagas` — antes ambos divergiam do cadastro real.
    """
    andar = db.query(Andar).filter(Andar.id == andar_id).first()
    if not andar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Andar não encontrado"
        )
    if quantidade < 1 or quantidade > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="quantidade deve estar entre 1 e 500",
        )
    if tipo not in {t.value for t in TipoVaga}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tipo inválido — use {[t.value for t in TipoVaga]}",
        )

    vagas_existentes = db.query(Vaga).filter(Vaga.andar_id == andar_id).count()
    codigos_existentes = {
        (codigo or "").upper()
        for (codigo,) in db.query(Vaga.codigo).filter(Vaga.andar_id == andar_id)
    }
    prefixo_codigo = prefixo_codigo.strip().upper()
    novas_vagas = []

    for i in range(quantidade):
        numero = vagas_existentes + i + 1
        codigo = f"{prefixo_codigo}{numero:02d}"
        while codigo in codigos_existentes:
            numero += 1
            codigo = f"{prefixo_codigo}{numero:02d}"
        codigos_existentes.add(codigo)
        vaga = Vaga(
            andar_id=andar_id,
            codigo=codigo,
            status=StatusVaga.LIVRE,
            tipo=tipo,
        )
        db.add(vaga)
        novas_vagas.append(vaga)

    andar.capacidade = vagas_existentes + quantidade
    est = db.query(Estacionamento).filter(Estacionamento.id == andar.estacionamento_id).first()
    if est:
        est.total_vagas = (est.total_vagas or 0) + quantidade

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

    _purgar_operacional(db, vaga_ids=[vaga_id])
    db.delete(vaga)
    db.commit()
    return {"mensagem": "Vaga removida com sucesso"}
