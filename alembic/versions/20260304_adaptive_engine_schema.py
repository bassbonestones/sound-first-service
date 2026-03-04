"""Add adaptive practice engine schema updates

Revision ID: 20260304_adaptive
Revises: 20260301_consolidated
Create Date: 2026-03-04

This migration adds:
- MaterialTeachesCapability: Junction for "teaches" relationship
- UserMaterialState: EMA + attempt tracking + status/shelf
- UserPitchFocusStats: Pitch/focus level performance tracking
- UserCapabilityEvidenceEvent: Append-only evidence log
- Collection + CollectionMaterial: Etude books, excerpt lists
- License + UserLicense: Content licensing scaffold
- Extensions to CapabilityV2: Evidence profile fields
- Extensions to MaterialAnalysis: Staged content dimensions
- Extensions to PracticeAttempt: Off-course tracking
- Extensions to UserCapabilityV2: Evidence count cache
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260304_adaptive'
down_revision = '20260301_consolidated'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # NEW TABLES
    # =========================================================================
    
    # License table (create first as it's referenced by collections)
    op.create_table(
        'licenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('license_type', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('metadata_json', sa.String(), nullable=True),
    )
    
    # UserLicense table
    op.create_table(
        'user_licenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('license_id', sa.Integer(), sa.ForeignKey('licenses.id'), nullable=False),
        sa.Column('purchased_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ul_user_license', 'user_licenses', ['user_id', 'license_id'], unique=True)
    
    # Collection table
    op.create_table(
        'collections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('source_type', sa.String(), nullable=True),
        sa.Column('license_id', sa.Integer(), sa.ForeignKey('licenses.id'), nullable=True),
        sa.Column('metadata_json', sa.String(), nullable=True),
    )
    
    # CollectionMaterial junction table
    op.create_table(
        'collection_materials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('collections.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=True),
    )
    op.create_index('ix_cm_collection', 'collection_materials', ['collection_id'])
    op.create_index('ix_cm_material', 'collection_materials', ['material_id'])
    op.create_index('ix_cm_collection_material', 'collection_materials', ['collection_id', 'material_id'], unique=True)
    
    # MaterialTeachesCapability junction table
    op.create_table(
        'material_teaches_capability',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities_v2.id'), nullable=False),
        sa.Column('weight', sa.Float(), default=1.0),
        sa.Column('notes', sa.String(), nullable=True),
    )
    op.create_index('ix_mtc_material', 'material_teaches_capability', ['material_id'])
    op.create_index('ix_mtc_capability', 'material_teaches_capability', ['capability_id'])
    op.create_index('ix_mtc_material_capability', 'material_teaches_capability', ['material_id', 'capability_id'], unique=True)
    
    # UserMaterialState table
    op.create_table(
        'user_material_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('ema_score', sa.Float(), default=0.0),
        sa.Column('attempt_count', sa.Integer(), default=0),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), default='UNEXPLORED'),
        sa.Column('shelf', sa.String(), default='DEFAULT'),
        sa.Column('guided_attempt_count', sa.Integer(), default=0),
        sa.Column('manual_attempt_count', sa.Integer(), default=0),
    )
    op.create_index('ix_ums_user_material', 'user_material_state', ['user_id', 'material_id'], unique=True)
    op.create_index('ix_ums_user_status', 'user_material_state', ['user_id', 'status'])
    op.create_index('ix_ums_user_shelf', 'user_material_state', ['user_id', 'shelf'])
    
    # UserPitchFocusStats table
    op.create_table(
        'user_pitch_focus_stats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('focus_card_id', sa.Integer(), sa.ForeignKey('focus_cards.id'), nullable=False),
        sa.Column('pitch_midi', sa.Integer(), nullable=False),
        sa.Column('context_type', sa.String(), nullable=False),
        sa.Column('context_id', sa.Integer(), nullable=True),
        sa.Column('ema_score', sa.Float(), default=0.0),
        sa.Column('attempt_count', sa.Integer(), default=0),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_upfs_unique', 'user_pitch_focus_stats', 
                    ['user_id', 'focus_card_id', 'pitch_midi', 'context_type', 'context_id'], unique=True)
    op.create_index('ix_upfs_user_context', 'user_pitch_focus_stats', ['user_id', 'context_type', 'context_id'])
    
    # UserCapabilityEvidenceEvent table
    op.create_table(
        'user_capability_evidence_event',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities_v2.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=True),
        sa.Column('practice_attempt_id', sa.Integer(), sa.ForeignKey('practice_attempts.id'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('credited_at', sa.DateTime(), nullable=False),
        sa.Column('is_off_course', sa.Boolean(), default=False),
    )
    op.create_index('ix_ucee_user_cap', 'user_capability_evidence_event', ['user_id', 'capability_id'])
    op.create_index('ix_ucee_user_cap_material', 'user_capability_evidence_event', 
                    ['user_id', 'capability_id', 'material_id'])
    
    # =========================================================================
    # EXTEND EXISTING TABLES
    # =========================================================================
    
    # CapabilityV2 - Evidence profile fields
    op.add_column('capabilities_v2', sa.Column('evidence_required_count', sa.Integer(), default=1))
    op.add_column('capabilities_v2', sa.Column('evidence_distinct_materials', sa.Boolean(), default=False))
    op.add_column('capabilities_v2', sa.Column('evidence_acceptance_threshold', sa.Integer(), default=4))
    op.add_column('capabilities_v2', sa.Column('evidence_qualifier_json', sa.String(), nullable=True))
    op.add_column('capabilities_v2', sa.Column('difficulty_weight', sa.Float(), default=1.0))
    
    # MaterialAnalysis - Staged content dimensions
    op.add_column('material_analysis', sa.Column('tonal_complexity_stage', sa.Integer(), nullable=True))
    op.add_column('material_analysis', sa.Column('interval_size_stage', sa.Integer(), nullable=True))
    op.add_column('material_analysis', sa.Column('rhythm_complexity_stage', sa.Integer(), nullable=True))
    op.add_column('material_analysis', sa.Column('range_usage_stage', sa.Integer(), nullable=True))
    op.add_column('material_analysis', sa.Column('melodic_predictability_stage', sa.Integer(), nullable=True))
    op.add_column('material_analysis', sa.Column('difficulty_index', sa.Float(), nullable=True))
    
    # Create indexes for stage filtering
    op.create_index('ix_ma_rhythm_stage', 'material_analysis', ['rhythm_complexity_stage'])
    op.create_index('ix_ma_range_stage', 'material_analysis', ['range_usage_stage'])
    op.create_index('ix_ma_tonal_stage', 'material_analysis', ['tonal_complexity_stage'])
    op.create_index('ix_ma_interval_stage', 'material_analysis', ['interval_size_stage'])
    
    # PracticeAttempt - Off-course tracking
    op.add_column('practice_attempts', sa.Column('is_off_course', sa.Boolean(), default=False))
    op.add_column('practice_attempts', sa.Column('was_eligible', sa.Boolean(), default=True))
    
    # UserCapabilityV2 - Evidence count cache
    op.add_column('user_capabilities_v2', sa.Column('evidence_count', sa.Integer(), default=0))


def downgrade() -> None:
    # =========================================================================
    # REMOVE COLUMN EXTENSIONS
    # =========================================================================
    
    # UserCapabilityV2
    op.drop_column('user_capabilities_v2', 'evidence_count')
    
    # PracticeAttempt
    op.drop_column('practice_attempts', 'is_off_course')
    op.drop_column('practice_attempts', 'was_eligible')
    
    # MaterialAnalysis indexes
    op.drop_index('ix_ma_interval_stage', 'material_analysis')
    op.drop_index('ix_ma_tonal_stage', 'material_analysis')
    op.drop_index('ix_ma_range_stage', 'material_analysis')
    op.drop_index('ix_ma_rhythm_stage', 'material_analysis')
    
    # MaterialAnalysis columns
    op.drop_column('material_analysis', 'difficulty_index')
    op.drop_column('material_analysis', 'melodic_predictability_stage')
    op.drop_column('material_analysis', 'range_usage_stage')
    op.drop_column('material_analysis', 'rhythm_complexity_stage')
    op.drop_column('material_analysis', 'interval_size_stage')
    op.drop_column('material_analysis', 'tonal_complexity_stage')
    
    # CapabilityV2
    op.drop_column('capabilities_v2', 'difficulty_weight')
    op.drop_column('capabilities_v2', 'evidence_qualifier_json')
    op.drop_column('capabilities_v2', 'evidence_acceptance_threshold')
    op.drop_column('capabilities_v2', 'evidence_distinct_materials')
    op.drop_column('capabilities_v2', 'evidence_required_count')
    
    # =========================================================================
    # DROP NEW TABLES
    # =========================================================================
    
    op.drop_table('user_capability_evidence_event')
    op.drop_table('user_pitch_focus_stats')
    op.drop_table('user_material_state')
    op.drop_table('material_teaches_capability')
    op.drop_table('collection_materials')
    op.drop_table('collections')
    op.drop_table('user_licenses')
    op.drop_table('licenses')
