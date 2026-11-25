"""Contabilizar tentativas do código SMTP de confirmação.

Revision ID: f067b001a1c0
Revises: f066b001a1c0
"""
from alembic import op
import sqlalchemy as sa

revision = "f067b001a1c0"
down_revision = "f066b001a1c0"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if "tokens_identidade" not in sa.inspect(conn).get_table_names():
        raise RuntimeError("Tabela tokens_identidade ausente; aplique migrações anteriores")
    cols = {c["name"] for c in sa.inspect(conn).get_columns("tokens_identidade")}
    if "tentativas" not in cols:
        op.add_column("tokens_identidade", sa.Column(
            "tentativas", sa.Integer(), nullable=False, server_default="0"
        ))


def downgrade():
    raise RuntimeError("Reverter a auditoria de tentativas exige backup e plano explícito")
