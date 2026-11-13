"""Gestor com vários shoppings + unicidade de financeiro por shopping.

Revision ID: c4e8b1d2f9a0
Revises: a7e41c9d0b52
Create Date: 2026-11-13 05:10:00.000000

Cria a tabela N:N `usuario_estacionamentos` e faz backfill do vínculo
principal (`usuarios.estacionamento_id`) para gestores/financeiros já
existentes — assim o escopo novo funciona em volumes antigos sem exigir
que o administrador recadastre todo mundo.
"""
import sqlalchemy as sa

from alembic import op

revision = "c4e8b1d2f9a0"
down_revision = "a7e41c9d0b52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario_estacionamentos",
        sa.Column("usuario_id", sa.String(), nullable=False),
        sa.Column("estacionamento_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuarios.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["estacionamento_id"], ["estacionamentos.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("usuario_id", "estacionamento_id"),
    )
    # Backfill: todo vínculo principal existente vira também uma linha N:N.
    op.execute(
        """
        INSERT INTO usuario_estacionamentos (usuario_id, estacionamento_id)
        SELECT id, estacionamento_id
        FROM usuarios
        WHERE estacionamento_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table("usuario_estacionamentos")
