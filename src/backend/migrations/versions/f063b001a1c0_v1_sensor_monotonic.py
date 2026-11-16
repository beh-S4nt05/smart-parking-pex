"""V1 PR63: monotonic accepted sequence per device.
Revision ID: f063b001a1c0
Revises: f061b001a1c0
"""
from alembic import op
import sqlalchemy as sa

revision = "f063b001a1c0"
down_revision = "f061b001a1c0"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "ultimo_seq" not in {col["name"] for col in sa.inspect(bind).get_columns("sensores")}:
        op.add_column("sensores", sa.Column("ultimo_seq", sa.Integer(), nullable=False, server_default="-1"))
    # Preserve previous event history when adding monotonic ordering.
    op.execute(sa.text("""
        UPDATE sensores
        SET ultimo_seq = COALESCE((
          SELECT MAX(e.seq) FROM sensor_eventos e
          WHERE e.sensor_id = sensores.id AND e.aplicado = true
        ), -1)
    """))


def downgrade():
    raise RuntimeError("Sequence rollback can allow replay. Restore a verified backup.")
