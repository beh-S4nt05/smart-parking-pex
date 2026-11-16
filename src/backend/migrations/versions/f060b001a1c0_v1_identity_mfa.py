"""V1 security 60: optional email verification and MFA state.

Revision ID: f060b001a1c0
Revises: d8f3a91c6e40
"""
from alembic import op
import sqlalchemy as sa

revision = "f060b001a1c0"
down_revision = "d8f3a91c6e40"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("usuarios")}
    for name, column in [
        ("email_verificado_em", sa.Column("email_verificado_em", sa.DateTime(timezone=True), nullable=True)),
        ("mfa_segredo_cifrado", sa.Column("mfa_segredo_cifrado", sa.Text(), nullable=True)),
        ("mfa_ativado_em", sa.Column("mfa_ativado_em", sa.DateTime(timezone=True), nullable=True)),
        ("mfa_ultimo_contador", sa.Column("mfa_ultimo_contador", sa.Integer(), nullable=False, server_default="-1")),
    ]:
        if name not in cols:
            op.add_column("usuarios", column)
    if "tokens_identidade" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "tokens_identidade",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("usuario_id", sa.String(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
            sa.Column("finalidade", sa.String(24), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumido_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    for name, cols in [("ix_tokens_identidade_usuario_id", ["usuario_id"]),("ix_tokens_identidade_token_hash", ["token_hash"])]:
        if name not in {idx["name"] for idx in sa.inspect(bind).get_indexes("tokens_identidade")}:
            op.create_index(name,"tokens_identidade",cols,unique=name.endswith("token_hash"))


def downgrade():
    # Explicitly refusing silent data loss; rollbacks must be coordinated.
    raise RuntimeError("Rollback of identity/security state is intentionally destructive. Restore from a verified backup.")
