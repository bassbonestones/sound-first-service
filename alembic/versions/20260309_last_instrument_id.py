"""Add last_instrument_id to users

Store which instrument the user last selected so we can restore it when they return.

Revision ID: 20260309_last_inst
Revises: 20260309_multi_instrument
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260309_last_inst'
down_revision = '20260309_multi_instrument'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add last_instrument_id column to users table
    # Note: SQLite doesn't support adding FK constraints via ALTER, so we just add the column
    op.add_column('users', sa.Column('last_instrument_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_instrument_id')
