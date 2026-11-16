"""V1 PR61: session inventory, refresh binding, server revocation.
Revision ID: f061b001a1c0
Revises: f060b001a1c0
"""
from alembic import op
import sqlalchemy as sa
revision = "f061b001a1c0"
down_revision = "f060b001a1c0"
branch_labels = None
depends_on = None


def upgrade():
    if "sessoes_acesso" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "sessoes_acesso",
            sa.Column("id",sa.String(),primary_key=True),
            sa.Column("usuario_id",sa.String(),sa.ForeignKey("usuarios.id",ondelete="CASCADE"),nullable=False),
            sa.Column("refresh_jti_hash",sa.String(64),nullable=False),
            sa.Column("dispositivo",sa.String(160),nullable=False),
            sa.Column("criado_em",sa.DateTime(timezone=True),server_default=sa.func.now()),
            sa.Column("ultimo_acesso_em",sa.DateTime(timezone=True)),
            sa.Column("expira_em",sa.DateTime(timezone=True),nullable=False),
            sa.Column("revogada_em",sa.DateTime(timezone=True)),
        )
    if "ix_sessoes_acesso_usuario_id" not in {x["name"] for x in sa.inspect(op.get_bind()).get_indexes("sessoes_acesso")}:
        op.create_index("ix_sessoes_acesso_usuario_id","sessoes_acesso",["usuario_id"])


def downgrade():
    raise RuntimeError("Restore a verified backup before reversing session state.")
