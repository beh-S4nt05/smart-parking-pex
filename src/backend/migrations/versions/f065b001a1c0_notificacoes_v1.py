"""V1 notifications: user inbox, preferences, watches and push outbox.
Revision ID: f065b001a1c0
Revises: f064b001a1c0
"""
from alembic import op
import sqlalchemy as sa

revision = "f065b001a1c0"
down_revision = "f064b001a1c0"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = inspector.get_table_names()
    if "notificacoes" not in existing:
        op.create_table(
            "notificacoes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("usuario_id", sa.String(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
            sa.Column("estacionamento_id", sa.String()),
            sa.Column("tipo", sa.String(40), nullable=False),
            sa.Column("titulo", sa.String(120), nullable=False),
            sa.Column("mensagem", sa.String(360), nullable=False),
            sa.Column("destino", sa.String(200)),
            sa.Column("referencia_tipo", sa.String(40)),
            sa.Column("referencia_id", sa.String()),
            sa.Column("chave_idempotencia", sa.String(250), nullable=False, unique=True),
            sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("lida_em", sa.DateTime(timezone=True)),
            sa.Column("expira_em", sa.DateTime(timezone=True)),
        )
        for col in ("usuario_id", "estacionamento_id", "tipo"):
            op.create_index("ix_notificacoes_" + col, "notificacoes", [col])
    if "preferencias_notificacao" not in existing:
        op.create_table(
            "preferencias_notificacao",
            sa.Column("usuario_id", sa.String(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("push_ativo", sa.Boolean(), nullable=False),
            sa.Column("reservas", sa.Boolean(), nullable=False),
            sa.Column("lembretes", sa.Boolean(), nullable=False),
            sa.Column("vagas", sa.Boolean(), nullable=False),
            sa.Column("financeiro", sa.Boolean(), nullable=False),
            sa.Column("resumo_diario", sa.Boolean(), nullable=False),
            sa.Column("silencio_inicio", sa.Integer(), nullable=False),
            sa.Column("silencio_fim", sa.Integer(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if "dispositivos_notificacao" not in existing:
        op.create_table(
            "dispositivos_notificacao",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("usuario_id", sa.String(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
            sa.Column("plataforma", sa.String(12), nullable=False),
            sa.Column("token_expo", sa.Text(), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("ultimo_uso_em", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_dispositivos_notificacao_usuario_id", "dispositivos_notificacao", ["usuario_id"])
    if "acompanhamentos_vagas" not in existing:
        op.create_table(
            "acompanhamentos_vagas",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("usuario_id", sa.String(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
            sa.Column("estacionamento_id", sa.String(), sa.ForeignKey("estacionamentos.id", ondelete="CASCADE"), nullable=False),
            sa.Column("andar_id", sa.String()),
            sa.Column("tipo_vaga", sa.String(30)),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("ultimo_aviso_em", sa.DateTime(timezone=True)),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        for col in ("usuario_id", "estacionamento_id"):
            op.create_index("ix_acompanhamentos_vagas_" + col, "acompanhamentos_vagas", [col])
    if "entregas_notificacao" not in existing:
        op.create_table(
            "entregas_notificacao",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("notificacao_id", sa.String(), sa.ForeignKey("notificacoes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("dispositivo_id", sa.String(), sa.ForeignKey("dispositivos_notificacao.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("tentativas", sa.Integer(), nullable=False),
            sa.Column("executar_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("expira_em", sa.DateTime(timezone=True)),
            sa.Column("ticket_id", sa.String()),
            sa.Column("ultimo_erro", sa.String(200)),
            sa.UniqueConstraint("notificacao_id", "dispositivo_id", name="uq_entrega_notif_dispositivo"),
        )
        for col in ("notificacao_id", "status"):
            op.create_index("ix_entregas_notificacao_" + col, "entregas_notificacao", [col])


def downgrade():
    # Preserve user inbox/audit trail unless explicitly backed up.
    raise RuntimeError("Notificações persistentes exigem backup e migração de reversão manual.")
