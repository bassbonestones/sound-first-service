"""Drop user_module_progress table

Module completion is now derived from UserCapability.mastered_at instead
of being tracked separately in UserModuleProgress.

Revision ID: 20260327_drop_user_module_progress
Revises: 20260325_add_tunes_table
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260327_drop_module_progress'
down_revision: Union[str, None] = '20260325_add_tunes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the user_module_progress table - no longer needed
    # Module completion is now derived from UserCapability.mastered_at
    op.drop_table('user_module_progress')


def downgrade() -> None:
    # Recreate the table if needed to rollback
    op.create_table(
        'user_module_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['teaching_modules.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_module_progress_user_module', 'user_module_progress', ['user_id', 'module_id'], unique=True)
    op.create_index('ix_user_module_progress_user_status', 'user_module_progress', ['user_id', 'status'], unique=False)
