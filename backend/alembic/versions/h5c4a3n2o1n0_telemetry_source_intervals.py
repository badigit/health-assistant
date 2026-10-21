"""Preserve source intervals for overlap-safe daily telemetry totals."""
from alembic import op
import sqlalchemy as sa

revision = 'h5c4a3n2o1n0'
down_revision = 'b1y2o3k4s5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('telemetry_data', sa.Column('start_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('telemetry_data', sa.Column('source_name', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('telemetry_data', 'source_name')
    op.drop_column('telemetry_data', 'start_timestamp')
