"""Add interval demand profile columns to material_analysis

Revision ID: 20260307_interval_profile
Revises: 20260307_rhythm_windowed
Create Date: 2026-03-07

Adds interval demand profile system columns:

New interval stages (replaces single interval_size_stage):
- interval_sustained_stage: Overall suitability (p75-driven, for assignment)
- interval_hazard_stage: Peak danger (max-driven, for warnings)
- legacy_interval_size_stage: Backward compat = max(sustained, hazard)

Interval profile data:
- interval_step_ratio: Proportion of intervals 0-2 semitones
- interval_skip_ratio: Proportion of intervals 3-5 semitones
- interval_leap_ratio: Proportion of intervals 6-11 semitones
- interval_large_leap_ratio: Proportion of intervals 12-17 semitones
- interval_extreme_leap_ratio: Proportion of intervals 18+ semitones
- interval_p50: Median interval (semitones)
- interval_p75: 75th percentile interval (semitones)
- interval_p90: 90th percentile interval (semitones)

Local clustering:
- interval_max_large_in_window: Max large leaps in any window
- interval_max_extreme_in_window: Max extreme leaps in any window
- interval_hardest_measures: JSON array of hardest measure numbers

This system correctly captures "globally moderate, locally brutal" pieces
by separating sustained challenge from peak hazard.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260307_interval_profile'
down_revision = '20260307_rhythm_windowed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New interval stages
    op.add_column('material_analysis', 
        sa.Column('interval_sustained_stage', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_hazard_stage', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('legacy_interval_size_stage', sa.Integer(), nullable=True))
    
    # Interval profile ratios
    op.add_column('material_analysis', 
        sa.Column('interval_step_ratio', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_skip_ratio', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_leap_ratio', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_large_leap_ratio', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_extreme_leap_ratio', sa.Float(), nullable=True))
    
    # Percentiles
    op.add_column('material_analysis', 
        sa.Column('interval_p50', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_p75', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_p90', sa.Integer(), nullable=True))
    
    # Local clustering
    op.add_column('material_analysis', 
        sa.Column('interval_max_large_in_window', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_max_extreme_in_window', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_hardest_measures', sa.String(), nullable=True))


def downgrade() -> None:
    # Local clustering
    op.drop_column('material_analysis', 'interval_hardest_measures')
    op.drop_column('material_analysis', 'interval_max_extreme_in_window')
    op.drop_column('material_analysis', 'interval_max_large_in_window')
    
    # Percentiles
    op.drop_column('material_analysis', 'interval_p90')
    op.drop_column('material_analysis', 'interval_p75')
    op.drop_column('material_analysis', 'interval_p50')
    
    # Profile ratios
    op.drop_column('material_analysis', 'interval_extreme_leap_ratio')
    op.drop_column('material_analysis', 'interval_large_leap_ratio')
    op.drop_column('material_analysis', 'interval_leap_ratio')
    op.drop_column('material_analysis', 'interval_skip_ratio')
    op.drop_column('material_analysis', 'interval_step_ratio')
    
    # Stages
    op.drop_column('material_analysis', 'legacy_interval_size_stage')
    op.drop_column('material_analysis', 'interval_hazard_stage')
    op.drop_column('material_analysis', 'interval_sustained_stage')
