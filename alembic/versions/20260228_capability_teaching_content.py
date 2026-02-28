"""Add teaching content fields to capabilities and create user_capability_progress table

Revision ID: 20260228_capability_teaching
Revises: a20260228_user_onboarding
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260228_capability_teaching'
down_revision = '20260228_curriculum_steps'
branch_labels = None
depends_on = None


def upgrade():
    # Add teaching content columns to capabilities table
    op.add_column('capabilities', sa.Column('domain', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('sequence_order', sa.Integer(), nullable=True))
    op.add_column('capabilities', sa.Column('display_name', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('explanation', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('visual_example_url', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('audio_example_url', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('quiz_type', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('quiz_question', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('quiz_options', sa.String(), nullable=True))
    op.add_column('capabilities', sa.Column('quiz_answer', sa.String(), nullable=True))
    
    # Create user_capability_progress table
    op.create_table(
        'user_capability_progress',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False),
        sa.Column('introduced_at', sa.DateTime(), nullable=True),
        sa.Column('quiz_passed', sa.Boolean(), default=False),
        sa.Column('times_refreshed', sa.Integer(), default=0),
    )
    
    # Create index for efficient lookups
    op.create_index('ix_user_capability_progress_user_id', 'user_capability_progress', ['user_id'])


def downgrade():
    # Drop user_capability_progress table
    op.drop_index('ix_user_capability_progress_user_id', 'user_capability_progress')
    op.drop_table('user_capability_progress')
    
    # Remove teaching content columns from capabilities
    op.drop_column('capabilities', 'quiz_answer')
    op.drop_column('capabilities', 'quiz_options')
    op.drop_column('capabilities', 'quiz_question')
    op.drop_column('capabilities', 'quiz_type')
    op.drop_column('capabilities', 'audio_example_url')
    op.drop_column('capabilities', 'visual_example_url')
    op.drop_column('capabilities', 'explanation')
    op.drop_column('capabilities', 'display_name')
    op.drop_column('capabilities', 'sequence_order')
    op.drop_column('capabilities', 'domain')
