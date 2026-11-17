"""V1: persist operational events for booking/cancel/check-in/payment.
Revision ID: f064b001a1c0
Revises: f063b001a1c0
"""

from alembic import op
import sqlalchemy as sa

revision = "f064b001a1c0"
down_revision = "f063b001a1c0"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "eventos_operacionais" in inspector.get_table_names():
        return
    op.create_table(
        "eventos_operacionais",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("estacionamento_id", sa.String(), nullable=False),
        sa.Column("usuario_id", sa.String(), nullable=True),
        sa.Column("reserva_id", sa.String(), nullable=True),
        sa.Column("vaga_id", sa.String(), nullable=True),
        sa.Column("historico_id", sa.String(), nullable=True),
        sa.Column("pagamento_id", sa.String(), nullable=True),
        sa.Column("evento", sa.String(length=40), nullable=False),
        sa.Column("origem", sa.String(length=30), nullable=False),
        sa.Column("valor", sa.Float(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for col in ("estacionamento_id", "usuario_id", "reserva_id", "evento", "criado_em"):
        op.create_index("ix_eventos_operacionais_" + col, "eventos_operacionais", [col])


def downgrade():
    # Não apagar a trilha de auditoria na reversão sem backup explícito.
    raise RuntimeError("Migração de auditoria irreversível automaticamente; restaure um backup verificado.")
