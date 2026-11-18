"""Timestamp of Expo ticket acceptance, independent of notification creation.

Revision ID: f066b001a1c0
Revises: f065b001a1c0
"""
from alembic import op
import sqlalchemy as sa

revision = "f066b001a1c0"
down_revision = "f065b001a1c0"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "entregas_notificacao" not in inspector.get_table_names():
        raise RuntimeError("Tabela de entregas ausente: aplicar f065 antes de f066")
    colunas = {col["name"] for col in inspector.get_columns("entregas_notificacao")}
    if "aceito_em" not in colunas:
        op.add_column("entregas_notificacao", sa.Column(
            "aceito_em", sa.DateTime(timezone=True), nullable=True
        ))


def downgrade():
    # A coluna faz parte da auditoria de entrega. Preservar dados no rollback.
    raise RuntimeError("Reverter f066 exige backup e plano explícito de perda de rastreio")
