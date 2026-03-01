"""Add mastery and teaching material fields to capabilities_v2 and max_melodic_interval to users

Revision ID: 20260228_mastery_fields
Revises: 20260228_capability_v2
Create Date: 2026-02-28

This migration adds:
1. introduction_material_id on capabilities_v2 - links to THE material that teaches this
2. mastery_type on capabilities_v2 - 'single', 'any_of_pool', 'multiple'
3. mastery_count on capabilities_v2 - how many materials needed for 'multiple' type
4. max_melodic_interval on users - replaces 24 individual interval capabilities
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260228_mastery_fields'
down_revision = '20260228_capability_v2'
branch_labels = None
depends_on = None


def upgrade():
    # Add teaching material linkage to capabilities_v2
    op.add_column('capabilities_v2', sa.Column(
        'introduction_material_id', 
        sa.Integer(), 
        sa.ForeignKey('materials.id'),
        nullable=True
    ))
    
    # Add mastery requirements to capabilities_v2
    op.add_column('capabilities_v2', sa.Column(
        'mastery_type',
        sa.String(),
        server_default='single',
        nullable=False
    ))
    op.add_column('capabilities_v2', sa.Column(
        'mastery_count',
        sa.Integer(),
        server_default='1',
        nullable=False
    ))
    
    # Add max_melodic_interval to users (replaces 24 interval capabilities)
    op.add_column('users', sa.Column(
        'max_melodic_interval',
        sa.String(),
        server_default='M2',  # Start with major 2nd
        nullable=True
    ))


def downgrade():
    op.drop_column('users', 'max_melodic_interval')
    op.drop_column('capabilities_v2', 'mastery_count')
    op.drop_column('capabilities_v2', 'mastery_type')
    op.drop_column('capabilities_v2', 'introduction_material_id')
