"""enhanced capability system with bitmasks

Revision ID: 20260228_capability_v2
Revises: a20260228_user_onboarding
Create Date: 2026-02-28

This migration adds:
1. capabilities_v2 table - enhanced capability model with prerequisites and bitmask support
2. material_capabilities junction table - replaces comma-separated IDs
3. material_analysis table - stores extracted MusicXML analysis
4. user_capabilities_v2 table - enhanced user capability tracking
5. user_complexity_scores table - continuous complexity dimensions
6. Bitmask columns on users and materials for O(1) eligibility checks
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260228_capability_v2'
down_revision = '20260228_capability_teaching'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Enhanced capabilities table
    op.create_table(
        'capabilities_v2',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('subdomain', sa.String(), nullable=True),
        sa.Column('requirement_type', sa.String(), default='required'),
        sa.Column('prerequisite_ids', sa.String(), nullable=True),
        sa.Column('bit_index', sa.Integer(), nullable=True, unique=True),
        sa.Column('sequence_order', sa.Integer(), nullable=True),
        sa.Column('explanation', sa.String(), nullable=True),
        sa.Column('visual_example_url', sa.String(), nullable=True),
        sa.Column('audio_example_url', sa.String(), nullable=True),
        sa.Column('quiz_type', sa.String(), nullable=True),
        sa.Column('quiz_question', sa.String(), nullable=True),
        sa.Column('quiz_options', sa.String(), nullable=True),
        sa.Column('quiz_answer', sa.String(), nullable=True),
        sa.Column('difficulty_tier', sa.Integer(), default=1),
    )
    op.create_index('ix_capability_v2_domain', 'capabilities_v2', ['domain'])
    op.create_index('ix_capability_v2_bit_index', 'capabilities_v2', ['bit_index'])
    
    # 2. Material-Capability junction table
    op.create_table(
        'material_capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities_v2.id'), nullable=False),
        sa.Column('is_required', sa.Boolean(), default=True),
        sa.Column('occurrence_count', sa.Integer(), default=1),
    )
    op.create_index('ix_material_capabilities_material', 'material_capabilities', ['material_id'])
    op.create_index('ix_material_capabilities_capability', 'material_capabilities', ['capability_id'])
    op.create_index('ix_material_capabilities_pair', 'material_capabilities', ['material_id', 'capability_id'], unique=True)
    
    # 3. Material analysis table
    op.create_table(
        'material_analysis',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False, unique=True),
        sa.Column('lowest_pitch', sa.String(), nullable=True),
        sa.Column('highest_pitch', sa.String(), nullable=True),
        sa.Column('range_semitones', sa.Integer(), nullable=True),
        sa.Column('pitch_density_low', sa.Float(), nullable=True),
        sa.Column('pitch_density_mid', sa.Float(), nullable=True),
        sa.Column('pitch_density_high', sa.Float(), nullable=True),
        sa.Column('trill_lowest', sa.String(), nullable=True),
        sa.Column('trill_highest', sa.String(), nullable=True),
        sa.Column('chromatic_complexity', sa.Float(), nullable=True),
        sa.Column('rhythmic_complexity', sa.Float(), nullable=True),
        sa.Column('reading_complexity', sa.Float(), nullable=True),
        sa.Column('tempo_marking', sa.String(), nullable=True),
        sa.Column('tempo_bpm', sa.Integer(), nullable=True),
        sa.Column('measure_count', sa.Integer(), nullable=True),
        sa.Column('estimated_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('raw_extraction_json', sa.String(), nullable=True),
    )
    
    # 4. Enhanced user capabilities table
    op.create_table(
        'user_capabilities_v2',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities_v2.id'), nullable=False),
        sa.Column('introduced_at', sa.DateTime(), nullable=True),
        sa.Column('mastered_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.Column('times_practiced', sa.Integer(), default=0),
        sa.Column('times_refreshed', sa.Integer(), default=0),
    )
    op.create_index('ix_user_capabilities_v2_pair', 'user_capabilities_v2', ['user_id', 'capability_id'], unique=True)
    op.create_index('ix_user_capabilities_v2_active', 'user_capabilities_v2', ['user_id', 'is_active'])
    
    # 5. User complexity scores table
    op.create_table(
        'user_complexity_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('max_chromatic_complexity', sa.Float(), default=1.0),
        sa.Column('max_rhythmic_complexity', sa.Float(), default=1.0),
        sa.Column('max_reading_complexity', sa.Float(), default=1.0),
        sa.Column('comfortable_chromatic', sa.Float(), default=1.0),
        sa.Column('comfortable_rhythmic', sa.Float(), default=1.0),
        sa.Column('comfortable_reading', sa.Float(), default=1.0),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    
    # 6. Add bitmask columns to users table (8 x 64-bit = 512 capabilities max)
    op.add_column('users', sa.Column('cap_mask_0', sa.BigInteger(), default=0))
    op.add_column('users', sa.Column('cap_mask_1', sa.BigInteger(), default=0))
    op.add_column('users', sa.Column('cap_mask_2', sa.BigInteger(), default=0))
    op.add_column('users', sa.Column('cap_mask_3', sa.BigInteger(), default=0))
    op.add_column('users', sa.Column('cap_mask_4', sa.BigInteger(), default=0))
    op.add_column('users', sa.Column('cap_mask_5', sa.BigInteger(), default=0))
    op.add_column('users', sa.Column('cap_mask_6', sa.BigInteger(), default=0))
    op.add_column('users', sa.Column('cap_mask_7', sa.BigInteger(), default=0))
    
    # 7. Add bitmask columns to materials table
    op.add_column('materials', sa.Column('req_cap_mask_0', sa.BigInteger(), default=0))
    op.add_column('materials', sa.Column('req_cap_mask_1', sa.BigInteger(), default=0))
    op.add_column('materials', sa.Column('req_cap_mask_2', sa.BigInteger(), default=0))
    op.add_column('materials', sa.Column('req_cap_mask_3', sa.BigInteger(), default=0))
    op.add_column('materials', sa.Column('req_cap_mask_4', sa.BigInteger(), default=0))
    op.add_column('materials', sa.Column('req_cap_mask_5', sa.BigInteger(), default=0))
    op.add_column('materials', sa.Column('req_cap_mask_6', sa.BigInteger(), default=0))
    op.add_column('materials', sa.Column('req_cap_mask_7', sa.BigInteger(), default=0))


def downgrade():
    # Remove bitmask columns from materials
    op.drop_column('materials', 'req_cap_mask_7')
    op.drop_column('materials', 'req_cap_mask_6')
    op.drop_column('materials', 'req_cap_mask_5')
    op.drop_column('materials', 'req_cap_mask_4')
    op.drop_column('materials', 'req_cap_mask_3')
    op.drop_column('materials', 'req_cap_mask_2')
    op.drop_column('materials', 'req_cap_mask_1')
    op.drop_column('materials', 'req_cap_mask_0')
    
    # Remove bitmask columns from users
    op.drop_column('users', 'cap_mask_7')
    op.drop_column('users', 'cap_mask_6')
    op.drop_column('users', 'cap_mask_5')
    op.drop_column('users', 'cap_mask_4')
    op.drop_column('users', 'cap_mask_3')
    op.drop_column('users', 'cap_mask_2')
    op.drop_column('users', 'cap_mask_1')
    op.drop_column('users', 'cap_mask_0')
    
    # Drop new tables
    op.drop_table('user_complexity_scores')
    op.drop_table('user_capabilities_v2')
    op.drop_table('material_analysis')
    op.drop_table('material_capabilities')
    op.drop_table('capabilities_v2')
