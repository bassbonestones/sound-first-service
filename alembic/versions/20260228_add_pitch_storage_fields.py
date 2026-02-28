
"""
Alembic migration script to add pitch storage fields to the materials table.
"""

# revision identifiers, used by Alembic.
revision = 'a20260228_pitch_fields'
down_revision = 'f2cc307cab56'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('materials', sa.Column('musicxml_canonical', sa.Text()))
    op.add_column('materials', sa.Column('original_key_center', sa.String(), nullable=True))
    op.add_column('materials', sa.Column('pitch_reference_type', sa.String()))
    op.add_column('materials', sa.Column('pitch_ref_json', sa.Text()))
    op.add_column('materials', sa.Column('spelling_policy', sa.String(), server_default='from_key'))

def downgrade():
    op.drop_column('materials', 'spelling_policy')
    op.drop_column('materials', 'pitch_ref_json')
    op.drop_column('materials', 'pitch_reference_type')
    op.drop_column('materials', 'original_key_center')
    op.drop_column('materials', 'musicxml_canonical')
