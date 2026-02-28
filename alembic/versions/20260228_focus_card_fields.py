"""add focus card fields

Revision ID: 20260228_focus_card_fields
Revises: a20260228_user_onboarding
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260228_focus_card_fields'
down_revision = 'a20260228_user_onboarding'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('focus_cards', sa.Column('description', sa.String(), nullable=True))
    op.add_column('focus_cards', sa.Column('category', sa.String(), nullable=True))
    op.add_column('focus_cards', sa.Column('attention_cue', sa.String(), nullable=True))
    op.add_column('focus_cards', sa.Column('micro_cues', sa.String(), nullable=True))
    op.add_column('focus_cards', sa.Column('prompts', sa.String(), nullable=True))


def downgrade():
    op.drop_column('focus_cards', 'prompts')
    op.drop_column('focus_cards', 'micro_cues')
    op.drop_column('focus_cards', 'attention_cue')
    op.drop_column('focus_cards', 'category')
    op.drop_column('focus_cards', 'description')
