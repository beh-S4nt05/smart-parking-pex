"""V1 PR65 — security events, additive only.
Revision ID: f065b001a1c0
Revises: f063b001a1c0
"""
from alembic import op
import sqlalchemy as sa

revision = "f065b001a1c0"
down_revision = "f063b001a1c0"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "eventos_seguranca" not in inspector.get_table_names():
        op.create_table(
            "eventos_seguranca",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("usuario_id", sa.String(), nullable=True),
            sa.Column("estacionamento_id", sa.String(), nullable=True),
            sa.Column("categoria", sa.String(32), nullable=False),
            sa.Column("operacao", sa.String(64), nullable=False),
            sa.Column("metodo", sa.String(8), nullable=False),
            sa.Column("status_http", sa.Integer(), nullable=False),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    for name, column in [
        ("ix_eventos_seguranca_usuario_id", ["usuario_id"]),
        ("ix_eventos_seguranca_estacionamento_id", ["estacionamento_id"]),
        ("ix_eventos_seguranca_categoria", ["categoria"]),
    ]:
        if name not in {x["name"] for x in sa.inspect(op.get_bind()).get_indexes("eventos_seguranca")}:
            op.create_index(name, "eventos_seguranca", column)


def downgrade():
    raise RuntimeError("Event audit history must not be deleted by automatic rollback.")
