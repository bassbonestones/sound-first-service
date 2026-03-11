"""Add keys_completed_json to user_lesson_progress for multi-key mastery tracking

Revision ID: 20260311_keys_completed
Revises: 20260310_rename_module_prereqs
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260311_keys_completed'
down_revision = '20260310_nullable_cap'
branch_labels = None
depends_on = None


def upgrade():
    # Add keys_completed_json column to track which starting notes/keys have been completed
    # This enables multi-key mastery (e.g., requiring fragment exercises to be completed in 2+ keys)
    op.add_column('user_lesson_progress', 
        sa.Column('keys_completed_json', sa.String(), server_default='[]', nullable=True)
    )


def downgrade():
    op.drop_column('user_lesson_progress', 'keys_completed_json')
