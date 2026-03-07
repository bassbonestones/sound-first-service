"""Add soft gate metrics columns to material_analysis

Revision ID: 20260307_soft_gates
Revises: 20260306_initial
Create Date: 2026-03-07

Adds new columns to material_analysis for soft gate metrics:
- density_notes_per_second: Tempo-adjusted note density
- tempo_difficulty_score: Combined tempo difficulty (0-1)
- interval_velocity_score: IVS score (0-1)
- unique_pitch_count: Distinct pitch classes (0-12)
- largest_interval_semitones: Max melodic leap
- note_density_per_measure: Notes per measure (tempo-independent)

Also changes rhythm_complexity_stage from Integer to Float (0-1 continuous).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260307_soft_gates'
down_revision = '20260306_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new soft gate metric columns
    op.add_column('material_analysis', 
        sa.Column('density_notes_per_second', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('tempo_difficulty_score', sa.Float(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('interval_velocity_score', sa.Float(), nullable=True))
    
    # Add additional analysis metrics
    op.add_column('material_analysis', 
        sa.Column('unique_pitch_count', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('largest_interval_semitones', sa.Integer(), nullable=True))
    op.add_column('material_analysis', 
        sa.Column('note_density_per_measure', sa.Float(), nullable=True))
    
    # Note: rhythm_complexity_stage type change from Integer to Float
    # SQLite doesn't support ALTER COLUMN TYPE, so we handle this via
    # application layer - values are already compatible (0-1 range)


def downgrade() -> None:
    op.drop_column('material_analysis', 'note_density_per_measure')
    op.drop_column('material_analysis', 'largest_interval_semitones')
    op.drop_column('material_analysis', 'unique_pitch_count')
    op.drop_column('material_analysis', 'interval_velocity_score')
    op.drop_column('material_analysis', 'tempo_difficulty_score')
    op.drop_column('material_analysis', 'density_notes_per_second')
