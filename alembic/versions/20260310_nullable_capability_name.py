"""Make capability_name nullable for modules without a capability.

Modules like range_expansion don't unlock a capability - they just expand the
user's comfort range. These modules have capability_name = NULL.

Revision ID: 20260310_nullable_cap
Revises: 20260310_rename_module_prereqs
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260310_nullable_cap'
down_revision = '20260310_rename_module_prereqs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite requires table recreation to change nullable constraints
    # Use batch mode for SQLite
    with op.batch_alter_table('teaching_modules') as batch_op:
        batch_op.alter_column('capability_name', nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('teaching_modules') as batch_op:
        batch_op.alter_column('capability_name', nullable=False)
