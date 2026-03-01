"""Consolidated schema - all tables

Revision ID: 20260301_consolidated
Revises: None
Create Date: 2026-03-01

This single migration creates the complete database schema.
Compatible with both SQLite (development) and PostgreSQL (production).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260301_consolidated'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # USERS TABLE
    # ==========================================================================
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('instrument', sa.String(), nullable=True),
        sa.Column('resonant_note', sa.String(), nullable=True),
        sa.Column('comfortable_capabilities', sa.String(), nullable=True),
        sa.Column('range_low', sa.String(), nullable=True),
        sa.Column('range_high', sa.String(), nullable=True),
        
        # Interval tracking (replaces 24 individual interval capabilities)
        sa.Column('max_melodic_interval', sa.String(), nullable=True, server_default='M2'),
        
        # Day 0 first-note experience tracking
        sa.Column('day0_completed', sa.Boolean(), server_default='0'),
        sa.Column('day0_stage', sa.Integer(), server_default='0'),
        
        # Bitmask columns for fast capability eligibility checks (8 x 64-bit = 512 capabilities)
        sa.Column('cap_mask_0', sa.BigInteger(), server_default='0'),
        sa.Column('cap_mask_1', sa.BigInteger(), server_default='0'),
        sa.Column('cap_mask_2', sa.BigInteger(), server_default='0'),
        sa.Column('cap_mask_3', sa.BigInteger(), server_default='0'),
        sa.Column('cap_mask_4', sa.BigInteger(), server_default='0'),
        sa.Column('cap_mask_5', sa.BigInteger(), server_default='0'),
        sa.Column('cap_mask_6', sa.BigInteger(), server_default='0'),
        sa.Column('cap_mask_7', sa.BigInteger(), server_default='0'),
    )
    
    # ==========================================================================
    # CAPABILITIES TABLE (legacy v1)
    # ==========================================================================
    op.create_table('capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=True),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('explanation', sa.String(), nullable=True),
        sa.Column('visual_example_url', sa.String(), nullable=True),
        sa.Column('audio_example_url', sa.String(), nullable=True),
        sa.Column('quiz_type', sa.String(), nullable=True),
        sa.Column('quiz_question', sa.String(), nullable=True),
        sa.Column('quiz_options', sa.String(), nullable=True),
        sa.Column('quiz_answer', sa.String(), nullable=True),
    )
    
    # ==========================================================================
    # MATERIALS TABLE
    # ==========================================================================
    op.create_table('materials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('allowed_keys', sa.String(), nullable=True),
        sa.Column('required_capability_ids', sa.String(), nullable=True),
        sa.Column('scaffolding_capability_ids', sa.String(), nullable=True),
        sa.Column('musicxml_canonical', sa.String(), nullable=True),
        sa.Column('original_key_center', sa.String(), nullable=True),
        sa.Column('pitch_reference_type', sa.String(), nullable=True),
        sa.Column('pitch_ref_json', sa.String(), nullable=True),
        sa.Column('spelling_policy', sa.String(), server_default='from_key'),
        
        # Bitmask columns for fast capability eligibility checks
        sa.Column('req_cap_mask_0', sa.BigInteger(), server_default='0'),
        sa.Column('req_cap_mask_1', sa.BigInteger(), server_default='0'),
        sa.Column('req_cap_mask_2', sa.BigInteger(), server_default='0'),
        sa.Column('req_cap_mask_3', sa.BigInteger(), server_default='0'),
        sa.Column('req_cap_mask_4', sa.BigInteger(), server_default='0'),
        sa.Column('req_cap_mask_5', sa.BigInteger(), server_default='0'),
        sa.Column('req_cap_mask_6', sa.BigInteger(), server_default='0'),
        sa.Column('req_cap_mask_7', sa.BigInteger(), server_default='0'),
    )
    
    # ==========================================================================
    # CAPABILITIES V2 TABLE (enhanced capability system)
    # ==========================================================================
    op.create_table('capabilities_v2',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('subdomain', sa.String(), nullable=True),
        sa.Column('requirement_type', sa.String(), server_default='required'),
        sa.Column('prerequisite_ids', sa.String(), nullable=True),
        sa.Column('bit_index', sa.Integer(), unique=True, nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=True),
        sa.Column('explanation', sa.String(), nullable=True),
        sa.Column('visual_example_url', sa.String(), nullable=True),
        sa.Column('audio_example_url', sa.String(), nullable=True),
        sa.Column('quiz_type', sa.String(), nullable=True),
        sa.Column('quiz_question', sa.String(), nullable=True),
        sa.Column('quiz_options', sa.String(), nullable=True),
        sa.Column('quiz_answer', sa.String(), nullable=True),
        sa.Column('difficulty_tier', sa.Integer(), server_default='1'),
        sa.Column('introduction_material_id', sa.Integer(), nullable=True),
        sa.Column('mastery_type', sa.String(), server_default='single'),
        sa.Column('mastery_count', sa.Integer(), server_default='1'),
    )
    op.create_index('ix_capability_domain', 'capabilities_v2', ['domain'])
    op.create_index('ix_capability_bit_index', 'capabilities_v2', ['bit_index'])
    
    # ==========================================================================
    # FOCUS CARDS TABLE
    # ==========================================================================
    op.create_table('focus_cards',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('attention_cue', sa.String(), nullable=True),
        sa.Column('micro_cues', sa.String(), nullable=True),
        sa.Column('prompts', sa.String(), nullable=True),
    )
    
    # ==========================================================================
    # USER CAPABILITIES (junction table)
    # ==========================================================================
    op.create_table('user_capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False),
    )
    
    # ==========================================================================
    # USER CAPABILITY PROGRESS TABLE
    # ==========================================================================
    op.create_table('user_capability_progress',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False),
        sa.Column('introduced_at', sa.DateTime(), nullable=True),
        sa.Column('quiz_passed', sa.Boolean(), server_default='0'),
        sa.Column('times_refreshed', sa.Integer(), server_default='0'),
    )
    
    # ==========================================================================
    # USER RANGES TABLE
    # ==========================================================================
    op.create_table('user_ranges',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('range_low', sa.String(), nullable=True),
        sa.Column('range_high', sa.String(), nullable=True),
    )
    
    # ==========================================================================
    # PRACTICE SESSIONS TABLE
    # ==========================================================================
    op.create_table('practice_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('practice_mode', sa.String(), server_default='guided'),
    )
    
    # ==========================================================================
    # MINI SESSIONS TABLE
    # ==========================================================================
    op.create_table('mini_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('practice_session_id', sa.Integer(), sa.ForeignKey('practice_sessions.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('key', sa.String(), nullable=True),
        sa.Column('focus_card_id', sa.Integer(), sa.ForeignKey('focus_cards.id'), nullable=True),
        sa.Column('goal_type', sa.String(), nullable=True),
        sa.Column('current_step_index', sa.Integer(), server_default='0'),
        sa.Column('is_completed', sa.Boolean(), server_default='0'),
        sa.Column('attempt_count', sa.Integer(), server_default='0'),
        sa.Column('strain_detected', sa.Boolean(), server_default='0'),
    )
    
    # ==========================================================================
    # CURRICULUM STEPS TABLE
    # ==========================================================================
    op.create_table('curriculum_steps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mini_session_id', sa.Integer(), sa.ForeignKey('mini_sessions.id'), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(), nullable=False),
        sa.Column('instruction', sa.String(), nullable=True),
        sa.Column('prompt', sa.String(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), server_default='0'),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
    )
    
    # ==========================================================================
    # PRACTICE ATTEMPTS TABLE
    # ==========================================================================
    op.create_table('practice_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('key', sa.String(), nullable=True),
        sa.Column('focus_card_id', sa.Integer(), sa.ForeignKey('focus_cards.id'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('fatigue', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
    )
    
    # ==========================================================================
    # MATERIAL CAPABILITIES (junction table for v2)
    # ==========================================================================
    op.create_table('material_capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities_v2.id'), nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default='1'),
        sa.Column('occurrence_count', sa.Integer(), server_default='1'),
    )
    op.create_index('ix_material_capabilities_material', 'material_capabilities', ['material_id'])
    op.create_index('ix_material_capabilities_capability', 'material_capabilities', ['capability_id'])
    op.create_index('ix_material_capability_pair', 'material_capabilities', ['material_id', 'capability_id'], unique=True)
    
    # ==========================================================================
    # MATERIAL ANALYSIS TABLE
    # ==========================================================================
    op.create_table('material_analysis',
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
    
    # ==========================================================================
    # USER CAPABILITIES V2 (junction table)
    # ==========================================================================
    op.create_table('user_capabilities_v2',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities_v2.id'), nullable=False),
        sa.Column('introduced_at', sa.DateTime(), nullable=True),
        sa.Column('mastered_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.Column('times_practiced', sa.Integer(), server_default='0'),
        sa.Column('times_refreshed', sa.Integer(), server_default='0'),
    )
    op.create_index('ix_user_capability_pair', 'user_capabilities_v2', ['user_id', 'capability_id'], unique=True)
    op.create_index('ix_user_capability_active', 'user_capabilities_v2', ['user_id', 'is_active'])
    
    # ==========================================================================
    # USER COMPLEXITY SCORES TABLE
    # ==========================================================================
    op.create_table('user_complexity_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('max_chromatic_complexity', sa.Float(), server_default='1.0'),
        sa.Column('max_rhythmic_complexity', sa.Float(), server_default='1.0'),
        sa.Column('max_reading_complexity', sa.Float(), server_default='1.0'),
        sa.Column('comfortable_chromatic', sa.Float(), server_default='1.0'),
        sa.Column('comfortable_rhythmic', sa.Float(), server_default='1.0'),
        sa.Column('comfortable_reading', sa.Float(), server_default='1.0'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('user_complexity_scores')
    op.drop_table('user_capabilities_v2')
    op.drop_table('material_analysis')
    op.drop_table('material_capabilities')
    op.drop_table('practice_attempts')
    op.drop_table('curriculum_steps')
    op.drop_table('mini_sessions')
    op.drop_table('practice_sessions')
    op.drop_table('user_ranges')
    op.drop_table('user_capability_progress')
    op.drop_table('user_capabilities')
    op.drop_table('focus_cards')
    op.drop_table('capabilities_v2')
    op.drop_table('materials')
    op.drop_table('capabilities')
    op.drop_table('users')
