"""
Alembic migration to add onboarding fields to User model: instrument, resonant_note, comfortable_capabilities.
"""
# revision identifiers, used by Alembic.
revision = 'a20260228_user_onboarding'
down_revision = 'a20260228_pitch_fields'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('instrument', sa.String(), nullable=True))
    op.add_column('users', sa.Column('resonant_note', sa.String(), nullable=True))
    op.add_column('users', sa.Column('comfortable_capabilities', sa.String(), nullable=True))

def downgrade():
    op.drop_column('users', 'comfortable_capabilities')
    op.drop_column('users', 'resonant_note')
    op.drop_column('users', 'instrument')
