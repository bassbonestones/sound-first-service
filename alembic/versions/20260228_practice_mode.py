"""Add practice_mode column to practice_sessions table

Revision ID: 20260228_practice_mode
Revises: 20260228_capability_v2
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260228_practice_mode'
down_revision = '20260228_capability_v2'
branch_labels = None
depends_on = None


def upgrade():
    # Add practice_mode column to practice_sessions table
    # Values: "guided" (default) or "self_directed"
    op.add_column('practice_sessions', sa.Column('practice_mode', sa.String(), server_default='guided'))


def downgrade():
    op.drop_column('practice_sessions', 'practice_mode')
