"""Consolidated schema - Sound First Service
================================================================================
This file represents the COMPLETE database schema as of 2026-03-08.
Use this for fresh database setup or future migration reset baseline.

Migration History (consolidated):
- 20260306_initial: Base schema (users, capabilities, materials, etc.)
- 20260307_soft_gates: Added soft gate metrics to material_analysis
- 20260307_rhythm_windowed: Added windowed complexity metrics
- 20260307_interval_profile: Added interval demand profile system
- 20260308_unified_scoring: Added unified scoring schema (JSON + indexed scores)

To reset migrations and use this consolidated schema:
1. Drop all tables or delete the database
2. Delete all files in alembic/versions/
3. Move this file to alembic/versions/20260308_consolidated.py
4. Run: alembic upgrade head
================================================================================
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260308_consolidated'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # USERS
    # ==========================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('instrument', sa.String(), nullable=True),
        sa.Column('resonant_note', sa.String(), nullable=True),
        sa.Column('comfortable_capabilities', sa.String(), nullable=True),
        sa.Column('range_low', sa.String(), nullable=True),
        sa.Column('range_high', sa.String(), nullable=True),
        sa.Column('max_melodic_interval', sa.String(), nullable=True, default='M2'),
        # Day 0 tracking
        sa.Column('day0_completed', sa.Boolean(), default=False),
        sa.Column('day0_stage', sa.Integer(), default=0),
        # Bitmask columns (8 x 64-bit = 512 capabilities max)
        sa.Column('cap_mask_0', sa.BigInteger(), default=0),
        sa.Column('cap_mask_1', sa.BigInteger(), default=0),
        sa.Column('cap_mask_2', sa.BigInteger(), default=0),
        sa.Column('cap_mask_3', sa.BigInteger(), default=0),
        sa.Column('cap_mask_4', sa.BigInteger(), default=0),
        sa.Column('cap_mask_5', sa.BigInteger(), default=0),
        sa.Column('cap_mask_6', sa.BigInteger(), default=0),
        sa.Column('cap_mask_7', sa.BigInteger(), default=0),
    )

    # ==========================================================================
    # CAPABILITIES (evidence-based skill nodes)
    # ==========================================================================
    op.create_table(
        'capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('subdomain', sa.String(), nullable=True),
        sa.Column('requirement_type', sa.String(), default='required'),
        sa.Column('prerequisite_ids', sa.String(), nullable=True),
        sa.Column('bit_index', sa.Integer(), nullable=True, unique=True),
        sa.Column('explanation', sa.String(), nullable=True),
        sa.Column('difficulty_tier', sa.Integer(), default=1),
        sa.Column('introduction_material_id', sa.Integer(), nullable=True),
        sa.Column('mastery_type', sa.String(), default='single'),
        sa.Column('mastery_count', sa.Integer(), default=1),
        # Evidence profile fields
        sa.Column('evidence_required_count', sa.Integer(), default=1),
        sa.Column('evidence_distinct_materials', sa.Boolean(), default=False),
        sa.Column('evidence_acceptance_threshold', sa.Integer(), default=4),
        sa.Column('evidence_qualifier_json', sa.String(), nullable=True),
        sa.Column('difficulty_weight', sa.Float(), default=1.0),
        # Soft gate requirements (JSON: {"dimension_name": threshold})
        sa.Column('soft_gate_requirements', sa.String(), nullable=True),
        # Archive status
        sa.Column('is_active', sa.Boolean(), default=True),
    )
    op.create_index('ix_capability_domain', 'capabilities', ['domain'])
    op.create_index('ix_capability_bit_index', 'capabilities', ['bit_index'])

    # ==========================================================================
    # MATERIALS (MusicXML exercises)
    # ==========================================================================
    op.create_table(
        'materials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('allowed_keys', sa.String(), nullable=True),
        sa.Column('required_capability_ids', sa.String(), nullable=True),
        sa.Column('scaffolding_capability_ids', sa.String(), nullable=True),
        sa.Column('musicxml_canonical', sa.String(), nullable=True),
        sa.Column('original_key_center', sa.String(), nullable=True),
        sa.Column('pitch_reference_type', sa.String(), nullable=True),
        sa.Column('pitch_ref_json', sa.String(), nullable=True),
        sa.Column('spelling_policy', sa.String(), default='from_key'),
        # Bitmask columns (8 x 64-bit = 512 capabilities max)
        sa.Column('req_cap_mask_0', sa.BigInteger(), default=0),
        sa.Column('req_cap_mask_1', sa.BigInteger(), default=0),
        sa.Column('req_cap_mask_2', sa.BigInteger(), default=0),
        sa.Column('req_cap_mask_3', sa.BigInteger(), default=0),
        sa.Column('req_cap_mask_4', sa.BigInteger(), default=0),
        sa.Column('req_cap_mask_5', sa.BigInteger(), default=0),
        sa.Column('req_cap_mask_6', sa.BigInteger(), default=0),
        sa.Column('req_cap_mask_7', sa.BigInteger(), default=0),
    )

    # ==========================================================================
    # FOCUS CARDS (curated practice topics)
    # ==========================================================================
    op.create_table(
        'focus_cards',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('attention_cue', sa.String(), nullable=True),
        sa.Column('micro_cues', sa.String(), nullable=True),
        sa.Column('prompts', sa.String(), nullable=True),
    )

    # ==========================================================================
    # USER CAPABILITIES (evidence-based tracking)
    # ==========================================================================
    op.create_table(
        'user_capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False),
        sa.Column('introduced_at', sa.DateTime(), nullable=True),
        sa.Column('mastered_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.Column('times_practiced', sa.Integer(), default=0),
        sa.Column('times_refreshed', sa.Integer(), default=0),
        sa.Column('evidence_count', sa.Integer(), default=0),
    )
    op.create_index('ix_user_capability_pair', 'user_capabilities', ['user_id', 'capability_id'], unique=True)
    op.create_index('ix_user_capability_active', 'user_capabilities', ['user_id', 'is_active'])

    # ==========================================================================
    # USER RANGES
    # ==========================================================================
    op.create_table(
        'user_ranges',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('range_low', sa.String(), nullable=True),
        sa.Column('range_high', sa.String(), nullable=True),
    )

    # ==========================================================================
    # PRACTICE SESSIONS
    # ==========================================================================
    op.create_table(
        'practice_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('practice_mode', sa.String(), default='guided'),
    )
    op.create_index('ix_practice_sessions_user_id', 'practice_sessions', ['user_id'])

    # ==========================================================================
    # MINI SESSIONS
    # ==========================================================================
    op.create_table(
        'mini_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('practice_session_id', sa.Integer(), sa.ForeignKey('practice_sessions.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('key', sa.String(), nullable=True),
        sa.Column('focus_card_id', sa.Integer(), sa.ForeignKey('focus_cards.id'), nullable=True),
        sa.Column('goal_type', sa.String(), nullable=True),
        sa.Column('current_step_index', sa.Integer(), default=0),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('attempt_count', sa.Integer(), default=0),
        sa.Column('strain_detected', sa.Boolean(), default=False),
    )
    op.create_index('ix_mini_sessions_practice_session_id', 'mini_sessions', ['practice_session_id'])

    # ==========================================================================
    # CURRICULUM STEPS
    # ==========================================================================
    op.create_table(
        'curriculum_steps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mini_session_id', sa.Integer(), sa.ForeignKey('mini_sessions.id'), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(), nullable=False),
        sa.Column('instruction', sa.String(), nullable=True),
        sa.Column('prompt', sa.String(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
    )
    op.create_index('ix_curriculum_steps_mini_session_id', 'curriculum_steps', ['mini_session_id'])

    # ==========================================================================
    # PRACTICE ATTEMPTS
    # ==========================================================================
    op.create_table(
        'practice_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('key', sa.String(), nullable=True),
        sa.Column('focus_card_id', sa.Integer(), sa.ForeignKey('focus_cards.id'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('fatigue', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('is_off_course', sa.Boolean(), default=False),
        sa.Column('was_eligible', sa.Boolean(), default=True),
    )
    op.create_index('ix_practice_attempts_user_id', 'practice_attempts', ['user_id'])

    # ==========================================================================
    # MATERIAL CAPABILITIES (junction table - what caps a material REQUIRES)
    # ==========================================================================
    op.create_table(
        'material_capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False, index=True),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False, index=True),
        sa.Column('is_required', sa.Boolean(), default=True),
        sa.Column('occurrence_count', sa.Integer(), default=1),
    )
    op.create_index('ix_material_capability_pair', 'material_capabilities', ['material_id', 'capability_id'], unique=True)

    # ==========================================================================
    # MATERIAL ANALYSIS (MusicXML analysis metrics)
    # Includes: soft gates, windowed metrics, interval profile, unified scoring
    # ==========================================================================
    op.create_table(
        'material_analysis',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), unique=True, nullable=False),
        
        # --- Range analysis ---
        sa.Column('lowest_pitch', sa.String(), nullable=True),
        sa.Column('highest_pitch', sa.String(), nullable=True),
        sa.Column('range_semitones', sa.Integer(), nullable=True),
        
        # --- Pitch density (what % of notes fall in each zone) ---
        sa.Column('pitch_density_low', sa.Float(), nullable=True),
        sa.Column('pitch_density_mid', sa.Float(), nullable=True),
        sa.Column('pitch_density_high', sa.Float(), nullable=True),
        
        # --- Trill range concerns ---
        sa.Column('trill_lowest', sa.String(), nullable=True),
        sa.Column('trill_highest', sa.String(), nullable=True),
        
        # --- Complexity scores (legacy 1-10 scale) ---
        sa.Column('chromatic_complexity', sa.Float(), nullable=True),
        sa.Column('rhythmic_complexity', sa.Float(), nullable=True),
        sa.Column('reading_complexity', sa.Float(), nullable=True),
        
        # --- Tempo ---
        sa.Column('tempo_marking', sa.String(), nullable=True),
        sa.Column('tempo_bpm', sa.Integer(), nullable=True),
        
        # --- Duration ---
        sa.Column('measure_count', sa.Integer(), nullable=True),
        sa.Column('estimated_duration_seconds', sa.Integer(), nullable=True),
        
        # --- Raw extraction data (JSON) ---
        sa.Column('raw_extraction_json', sa.String(), nullable=True),
        
        # --- Staged content dimensions (legacy) ---
        sa.Column('tonal_complexity_stage', sa.Integer(), nullable=True),
        sa.Column('interval_size_stage', sa.Integer(), nullable=True),  # DEPRECATED: use interval_sustained_stage
        sa.Column('rhythm_complexity_stage', sa.Float(), nullable=True),  # 0-1 continuous (global)
        sa.Column('range_usage_stage', sa.Integer(), nullable=True),
        sa.Column('melodic_predictability_stage', sa.Integer(), nullable=True),
        sa.Column('difficulty_index', sa.Float(), nullable=True),
        
        # --- Soft gate metrics (Phase 2) ---
        sa.Column('density_notes_per_second', sa.Float(), nullable=True),
        sa.Column('tempo_difficulty_score', sa.Float(), nullable=True),
        sa.Column('interval_velocity_score', sa.Float(), nullable=True),  # global
        sa.Column('interval_velocity_peak', sa.Float(), nullable=True),   # windowed max
        sa.Column('interval_velocity_p95', sa.Float(), nullable=True),    # windowed 95th percentile
        sa.Column('unique_pitch_count', sa.Integer(), nullable=True),
        sa.Column('largest_interval_semitones', sa.Integer(), nullable=True),
        sa.Column('note_density_per_measure', sa.Float(), nullable=True),
        
        # --- Windowed rhythm complexity ---
        sa.Column('rhythm_complexity_peak', sa.Float(), nullable=True),
        sa.Column('rhythm_complexity_p95', sa.Float(), nullable=True),
        
        # --- Interval demand profile system ---
        # New staged assessments (replaces interval_size_stage)
        sa.Column('interval_sustained_stage', sa.Integer(), nullable=True),  # p75-driven, for assignment
        sa.Column('interval_hazard_stage', sa.Integer(), nullable=True),     # max-driven, for warnings
        sa.Column('legacy_interval_size_stage', sa.Integer(), nullable=True),# max(sustained, hazard) for compat
        
        # Interval profile ratios
        sa.Column('interval_step_ratio', sa.Float(), nullable=True),        # 0-2 semitones
        sa.Column('interval_skip_ratio', sa.Float(), nullable=True),        # 3-5 semitones
        sa.Column('interval_leap_ratio', sa.Float(), nullable=True),        # 6-11 semitones
        sa.Column('interval_large_leap_ratio', sa.Float(), nullable=True),  # 12-17 semitones
        sa.Column('interval_extreme_leap_ratio', sa.Float(), nullable=True),# 18+ semitones
        
        # Interval percentiles
        sa.Column('interval_p50', sa.Integer(), nullable=True),  # median
        sa.Column('interval_p75', sa.Integer(), nullable=True),
        sa.Column('interval_p90', sa.Integer(), nullable=True),
        
        # Local clustering
        sa.Column('interval_max_large_in_window', sa.Integer(), nullable=True),
        sa.Column('interval_max_extreme_in_window', sa.Integer(), nullable=True),
        sa.Column('interval_hardest_measures', sa.String(), nullable=True),  # JSON array
        
        # =======================================================================
        # UNIFIED SCORING SCHEMA (Phase 4) - Facet-aware domain analysis
        # =======================================================================
        sa.Column('analysis_schema_version', sa.Integer(), nullable=True, server_default='1'),
        
        # Full domain analysis JSON (preserves all facets, bands, flags, confidence)
        sa.Column('interval_analysis_json', sa.Text(), nullable=True),
        sa.Column('rhythm_analysis_json', sa.Text(), nullable=True),
        sa.Column('tonal_analysis_json', sa.Text(), nullable=True),
        sa.Column('tempo_analysis_json', sa.Text(), nullable=True),
        sa.Column('range_analysis_json', sa.Text(), nullable=True),
        sa.Column('throughput_analysis_json', sa.Text(), nullable=True),
        
        # Indexed primary scores for fast filtering/ranking (nullable for instrument-dependent)
        sa.Column('interval_primary_score', sa.Float(), nullable=True),
        sa.Column('rhythm_primary_score', sa.Float(), nullable=True),
        sa.Column('tonal_primary_score', sa.Float(), nullable=True),
        sa.Column('tempo_primary_score', sa.Float(), nullable=True),
        sa.Column('range_primary_score', sa.Float(), nullable=True),
        sa.Column('throughput_primary_score', sa.Float(), nullable=True),
        
        # Composite scores
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('interaction_bonus', sa.Float(), nullable=True),
    )
    
    # Indexes for unified scoring (fast score-based queries)
    op.create_index('ix_material_analysis_interval_primary_score', 'material_analysis', ['interval_primary_score'])
    op.create_index('ix_material_analysis_rhythm_primary_score', 'material_analysis', ['rhythm_primary_score'])
    op.create_index('ix_material_analysis_tonal_primary_score', 'material_analysis', ['tonal_primary_score'])
    op.create_index('ix_material_analysis_tempo_primary_score', 'material_analysis', ['tempo_primary_score'])
    op.create_index('ix_material_analysis_range_primary_score', 'material_analysis', ['range_primary_score'])
    op.create_index('ix_material_analysis_throughput_primary_score', 'material_analysis', ['throughput_primary_score'])
    op.create_index('ix_material_analysis_overall_score', 'material_analysis', ['overall_score'])

    # ==========================================================================
    # USER COMPLEXITY SCORES
    # ==========================================================================
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

    # ==========================================================================
    # LICENSES
    # ==========================================================================
    op.create_table(
        'licenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('license_type', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('metadata_json', sa.String(), nullable=True),
    )

    # ==========================================================================
    # USER LICENSES
    # ==========================================================================
    op.create_table(
        'user_licenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('license_id', sa.Integer(), sa.ForeignKey('licenses.id'), nullable=False),
        sa.Column('purchased_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ul_user_license', 'user_licenses', ['user_id', 'license_id'], unique=True)

    # ==========================================================================
    # COLLECTIONS
    # ==========================================================================
    op.create_table(
        'collections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('source_type', sa.String(), nullable=True),
        sa.Column('license_id', sa.Integer(), sa.ForeignKey('licenses.id'), nullable=True),
        sa.Column('metadata_json', sa.String(), nullable=True),
    )

    # ==========================================================================
    # COLLECTION MATERIALS (junction)
    # ==========================================================================
    op.create_table(
        'collection_materials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('collections.id'), nullable=False, index=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False, index=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
    )
    op.create_index('ix_cm_collection_material', 'collection_materials', ['collection_id', 'material_id'], unique=True)

    # ==========================================================================
    # MATERIAL TEACHES CAPABILITY (pedagogical relationship)
    # ==========================================================================
    op.create_table(
        'material_teaches_capability',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False, index=True),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False, index=True),
        sa.Column('weight', sa.Float(), default=1.0),
        sa.Column('notes', sa.String(), nullable=True),
    )
    op.create_index('ix_mtc_material_capability', 'material_teaches_capability', ['material_id', 'capability_id'], unique=True)

    # ==========================================================================
    # USER MATERIAL STATE (per-user material mastery tracking)
    # ==========================================================================
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

    # ==========================================================================
    # USER PITCH FOCUS STATS
    # ==========================================================================
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

    # ==========================================================================
    # USER CAPABILITY EVIDENCE EVENT (evidence event log)
    # ==========================================================================
    op.create_table(
        'user_capability_evidence_event',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=True),
        sa.Column('practice_attempt_id', sa.Integer(), sa.ForeignKey('practice_attempts.id'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('credited_at', sa.DateTime(), nullable=False),
        sa.Column('is_off_course', sa.Boolean(), default=False),
    )
    op.create_index('ix_ucee_user_cap', 'user_capability_evidence_event', ['user_id', 'capability_id'])
    op.create_index('ix_ucee_user_cap_material', 'user_capability_evidence_event', 
                    ['user_id', 'capability_id', 'material_id'])

    # ==========================================================================
    # SOFT GATE RULES
    # ==========================================================================
    op.create_table(
        'soft_gate_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('dimension_name', sa.String(), unique=True, nullable=False),
        sa.Column('frontier_buffer', sa.Float(), nullable=False),
        sa.Column('promotion_step', sa.Float(), nullable=False),
        sa.Column('min_attempts', sa.Integer(), nullable=False),
        sa.Column('success_rating_threshold', sa.Integer(), default=4),
        sa.Column('success_required_count', sa.Integer(), nullable=False),
        sa.Column('success_window_count', sa.Integer(), nullable=True),
        sa.Column('decay_halflife_days', sa.Float(), nullable=True),
    )

    # ==========================================================================
    # USER SOFT GATE STATE
    # ==========================================================================
    op.create_table(
        'user_soft_gate_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('dimension_name', sa.String(), nullable=False),
        sa.Column('comfortable_value', sa.Float(), nullable=False, default=0.0),
        sa.Column('max_demonstrated_value', sa.Float(), nullable=False, default=0.0),
        sa.Column('frontier_success_ema', sa.Float(), nullable=False, default=0.0),
        sa.Column('frontier_attempt_count_since_last_promo', sa.Integer(), nullable=False, default=0),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_usgs_user_dimension', 'user_soft_gate_state', ['user_id', 'dimension_name'], unique=True)
    op.create_index('ix_usgs_user', 'user_soft_gate_state', ['user_id'])


def downgrade() -> None:
    # Drop all tables in reverse order of creation
    op.drop_table('user_soft_gate_state')
    op.drop_table('soft_gate_rules')
    op.drop_table('user_capability_evidence_event')
    op.drop_table('user_pitch_focus_stats')
    op.drop_table('user_material_state')
    op.drop_table('material_teaches_capability')
    op.drop_table('collection_materials')
    op.drop_table('collections')
    op.drop_table('user_licenses')
    op.drop_table('licenses')
    op.drop_table('user_complexity_scores')
    op.drop_table('material_analysis')  # Includes unified scoring indexes
    op.drop_table('material_capabilities')
    op.drop_table('practice_attempts')
    op.drop_table('curriculum_steps')
    op.drop_table('mini_sessions')
    op.drop_table('practice_sessions')
    op.drop_table('user_ranges')
    op.drop_table('user_capabilities')
    op.drop_table('focus_cards')
    op.drop_table('materials')
    op.drop_table('capabilities')
    op.drop_table('users')
