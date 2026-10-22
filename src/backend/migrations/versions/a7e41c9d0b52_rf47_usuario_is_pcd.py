"""rf47: usuarios.is_pcd (autodeclaração PCD do cadastro)

Revision ID: a7e41c9d0b52
Revises: 3c79cee6fe1f
Create Date: 2026-10-22 18:30:00.000000

Coluna nova com server_default=False: tabela existente ganha "comum" para
todos os registros atuais — exatamente a semântica da RF-47 (quem NÃO
declarou é motorista comum). Funcional em Postgres e SQLite sem batch.
"""
import sqlalchemy as sa

from alembic import op

revision = "a7e41c9d0b52"
down_revision = "3c79cee6fe1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("is_pcd", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "is_pcd")
