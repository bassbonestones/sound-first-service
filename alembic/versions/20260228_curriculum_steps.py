"""add curriculum steps and mini session tracking

Revision ID: 20260228_curriculum_steps
Revises: 20260228_focus_card_fields
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260228_curriculum_steps'
down_revision = '20260228_focus_card_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add range fields to users
    op.add_column('users', sa.Column('range_low', sa.String(), nullable=True))
    op.add_column('users', sa.Column('range_high', sa.String(), nullable=True))
    
    # Add tracking fields to mini_sessions
    op.add_column('mini_sessions', sa.Column('current_step_index', sa.Integer(), default=0))
    op.add_column('mini_sessions', sa.Column('is_completed', sa.Boolean(), default=False))
    op.add_column('mini_sessions', sa.Column('attempt_count', sa.Integer(), default=0))
    op.add_column('mini_sessions', sa.Column('strain_detected', sa.Boolean(), default=False))
    
    # Create curriculum_steps table
    op.create_table(
        'curriculum_steps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mini_session_id', sa.Integer(), sa.ForeignKey('mini_sessions.id'), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(), nullable=False),
        sa.Column('instruction', sa.String()),
        sa.Column('prompt', sa.String()),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('curriculum_steps')
    op.drop_column('mini_sessions', 'strain_detected')
    op.drop_column('mini_sessions', 'attempt_count')
    op.drop_column('mini_sessions', 'is_completed')
    op.drop_column('mini_sessions', 'current_step_index')
    op.drop_column('users', 'range_high')
    op.drop_column('users', 'range_low')
