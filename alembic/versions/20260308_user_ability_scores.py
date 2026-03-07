"""Add user ability scores for unified scoring (Phase 7)

This migration adds domain ability score columns to user_complexity_scores
to track user's demonstrated competence on each unified scoring domain.

Revision ID: 20260308_user_ability
Revises: 20260308_consolidated
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260308_user_ability'
down_revision = '20260308_consolidated'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add domain ability score columns (0.0-1.0)
    op.add_column('user_complexity_scores',
        sa.Column('interval_ability_score', sa.Float(), nullable=True, default=0.0))
    op.add_column('user_complexity_scores',
        sa.Column('rhythm_ability_score', sa.Float(), nullable=True, default=0.0))
    op.add_column('user_complexity_scores',
        sa.Column('tonal_ability_score', sa.Float(), nullable=True, default=0.0))
    op.add_column('user_complexity_scores',
        sa.Column('tempo_ability_score', sa.Float(), nullable=True, default=0.0))
    op.add_column('user_complexity_scores',
        sa.Column('range_ability_score', sa.Float(), nullable=True, default=0.0))
    op.add_column('user_complexity_scores',
        sa.Column('throughput_ability_score', sa.Float(), nullable=True, default=0.0))
    
    # Add demonstrated stage columns (0-6)
    op.add_column('user_complexity_scores',
        sa.Column('interval_demonstrated_stage', sa.Integer(), nullable=True, default=0))
    op.add_column('user_complexity_scores',
        sa.Column('rhythm_demonstrated_stage', sa.Integer(), nullable=True, default=0))
    op.add_column('user_complexity_scores',
        sa.Column('tonal_demonstrated_stage', sa.Integer(), nullable=True, default=0))
    op.add_column('user_complexity_scores',
        sa.Column('tempo_demonstrated_stage', sa.Integer(), nullable=True, default=0))
    op.add_column('user_complexity_scores',
        sa.Column('range_demonstrated_stage', sa.Integer(), nullable=True, default=0))
    op.add_column('user_complexity_scores',
        sa.Column('throughput_demonstrated_stage', sa.Integer(), nullable=True, default=0))
    
    # Create indexes for fast eligibility filtering
    op.create_index('ix_ucs_interval_ability', 'user_complexity_scores', ['interval_ability_score'])
    op.create_index('ix_ucs_rhythm_ability', 'user_complexity_scores', ['rhythm_ability_score'])
    op.create_index('ix_ucs_tonal_ability', 'user_complexity_scores', ['tonal_ability_score'])
    op.create_index('ix_ucs_tempo_ability', 'user_complexity_scores', ['tempo_ability_score'])
    op.create_index('ix_ucs_range_ability', 'user_complexity_scores', ['range_ability_score'])
    op.create_index('ix_ucs_throughput_ability', 'user_complexity_scores', ['throughput_ability_score'])
    
    # Set default values for existing rows
    op.execute("""
        UPDATE user_complexity_scores SET
            interval_ability_score = 0.0,
            rhythm_ability_score = 0.0,
            tonal_ability_score = 0.0,
            tempo_ability_score = 0.0,
            range_ability_score = 0.0,
            throughput_ability_score = 0.0,
            interval_demonstrated_stage = 0,
            rhythm_demonstrated_stage = 0,
            tonal_demonstrated_stage = 0,
            tempo_demonstrated_stage = 0,
            range_demonstrated_stage = 0,
            throughput_demonstrated_stage = 0
        WHERE interval_ability_score IS NULL
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_ucs_interval_ability', table_name='user_complexity_scores')
    op.drop_index('ix_ucs_rhythm_ability', table_name='user_complexity_scores')
    op.drop_index('ix_ucs_tonal_ability', table_name='user_complexity_scores')
    op.drop_index('ix_ucs_tempo_ability', table_name='user_complexity_scores')
    op.drop_index('ix_ucs_range_ability', table_name='user_complexity_scores')
    op.drop_index('ix_ucs_throughput_ability', table_name='user_complexity_scores')
    
    # Drop columns
    op.drop_column('user_complexity_scores', 'interval_ability_score')
    op.drop_column('user_complexity_scores', 'rhythm_ability_score')
    op.drop_column('user_complexity_scores', 'tonal_ability_score')
    op.drop_column('user_complexity_scores', 'tempo_ability_score')
    op.drop_column('user_complexity_scores', 'range_ability_score')
    op.drop_column('user_complexity_scores', 'throughput_ability_score')
    op.drop_column('user_complexity_scores', 'interval_demonstrated_stage')
    op.drop_column('user_complexity_scores', 'rhythm_demonstrated_stage')
    op.drop_column('user_complexity_scores', 'tonal_demonstrated_stage')
    op.drop_column('user_complexity_scores', 'tempo_demonstrated_stage')
    op.drop_column('user_complexity_scores', 'range_demonstrated_stage')
    op.drop_column('user_complexity_scores', 'throughput_demonstrated_stage')
