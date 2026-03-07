"""Add windowed complexity columns to material_analysis

Revision ID: 20260307_rhythm_windowed
Revises: 20260307_soft_gates
Create Date: 2026-03-07

Adds windowed metrics for longer pieces (>= 32 quarter lengths):

Rhythm complexity:
- rhythm_complexity_peak: Maximum score across sliding windows (0-1)
- rhythm_complexity_p95: 95th percentile window score (0-1)

Interval velocity:
- interval_velocity_peak: Maximum IVS across sliding windows (0-1)
- interval_velocity_p95: 95th percentile window IVS (0-1)

These solve the "mostly easy except one hard passage" problem by
detecting peak difficulty regions.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260307_rhythm_windowed'
down_revision = '20260307_soft_gates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add windowed rhythm complexity columns
    op.add_column('material_analysis', 
        sa.Column('rhythm_complexity_peak', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('rhythm_complexity_p95', sa.Float(), nullable=True))
    # Add windowed interval velocity columns
    op.add_column('material_analysis', 
        sa.Column('interval_velocity_peak', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_velocity_p95', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('material_analysis', 'interval_velocity_p95')
    op.drop_column('material_analysis', 'interval_velocity_peak')
    op.drop_column('material_analysis', 'rhythm_complexity_p95')
    op.drop_column('material_analysis', 'rhythm_complexity_peak')
