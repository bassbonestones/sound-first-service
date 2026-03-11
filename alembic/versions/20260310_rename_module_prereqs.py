"""Rename prerequisite_module_ids to prerequisite_capability_names.

Modules now track prerequisite capabilities (not modules) to determine availability.
When a module's capability is mastered, that unlocks subsequent modules.

Revision ID: 20260310_rename_module_prereqs
Revises: 20260309_last_inst
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260310_rename_module_prereqs'
down_revision = '20260309_last_inst'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename the column from prerequisite_module_ids to prerequisite_capability_names
    op.alter_column(
        'teaching_modules',
        'prerequisite_module_ids',
        new_column_name='prerequisite_capability_names'
    )


def downgrade() -> None:
    # Revert the column name
    op.alter_column(
        'teaching_modules',
        'prerequisite_capability_names',
        new_column_name='prerequisite_module_ids'
    )
