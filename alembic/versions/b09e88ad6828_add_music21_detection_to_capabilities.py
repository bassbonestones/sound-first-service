"""add_music21_detection_to_capabilities

Revision ID: b09e88ad6828
Revises: 20260308_user_ability
Create Date: 2026-03-07 12:35:11.054185

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b09e88ad6828'
down_revision = '20260308_user_ability'
branch_labels = None
depends_on = None


def upgrade():
    # Add music21_detection_json column to capabilities table
    op.add_column('capabilities', sa.Column('music21_detection_json', sa.String(), nullable=True))


def downgrade():
    # Remove music21_detection_json column from capabilities table
    op.drop_column('capabilities', 'music21_detection_json')
