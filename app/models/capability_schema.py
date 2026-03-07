"""
Enhanced Capability Schema for Sound First

This module defines the comprehensive capability system for musical literacy tracking.

Architecture:
- SOURCE OF TRUTH: Normalized tables (capabilities, material_capabilities, user_capabilities)
- FAST PATH: Bitmask columns on users and materials for O(1) eligibility checks

Capability Domains:
- clef: treble_clef, bass_clef, alto_clef, tenor_clef
- time_signature: 4_4, 3_4, 2_4, 6_8, etc.
- key_signature: c_major, g_major, d_major, etc. (for reading, not ear-playing)
- note_value: whole_note, half_note, quarter_note, eighth_note, sixteenth_note, dotted variants
- rest: whole_rest, half_rest, quarter_rest, eighth_rest, sixteenth_rest
- tuplet: triplet, quintuplet, septuplet, etc.
- interval_melodic: m2_up, M2_up, m3_up, M3_up, P4_up, etc. (with direction)
- interval_harmonic: m2, M2, m3, M3, P4, etc.
- dynamic: pp, p, mp, mf, f, ff, sfz, sfp
- dynamic_change: crescendo, diminuendo, subito_forte, etc.
- articulation: staccato, legato, accent, tenuto, marcato, sforzando
- ornament: trill, mordent, turn, grace_note, appoggiatura
- tempo_term: allegro, andante, largo, presto, etc.
- expression_term: dolce, cantabile, espressivo, con_brio, etc.
- repeat_structure: repeat_sign, first_ending, second_ending, dc, ds, coda, segno
- notation_symbol: fermata, breath_mark, chord_symbol, figured_bass
- multivoice: two_voices, three_voices, etc.

Requirement Types:
- 'required': Must be taught and learned before material is eligible
- 'learnable_in_context': Can be introduced with the material if simple enough
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, BigInteger, Float, Index
from sqlalchemy.orm import relationship
from . import Base


class Capability(Base):
    """
    Capability model with prerequisites and bitmask support.
    
    The bit_index field maps this capability to a specific bit position
    for fast eligibility checking. Capabilities 0-63 go in cap_mask_0,
    64-127 in cap_mask_1, etc.
    """
    __tablename__ = 'capabilities'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "triplet_eighth"
    display_name = Column(String, nullable=True)  # e.g., "Eighth-Note Triplet"
    
    # Classification
    domain = Column(String, nullable=False)  # clef, time_signature, interval_melodic, etc.
    subdomain = Column(String, nullable=True)  # e.g., for intervals: "ascending", "descending"
    
    # Requirement classification
    requirement_type = Column(String, default='required')  # 'required' | 'learnable_in_context'
    
    # Prerequisites (JSON array of capability IDs)
    prerequisite_ids = Column(String, nullable=True)  # e.g., "[12, 15]" - must know these first
    
    # Bitmask optimization
    bit_index = Column(Integer, nullable=True, unique=True)  # 0-511 for 8 x 64-bit masks
    
    # Teaching content
    explanation = Column(String, nullable=True)  # Teaching text
    
    # Metadata
    difficulty_tier = Column(Integer, default=1)  # 1=beginner, 2=intermediate, 3=advanced
    
    # Teaching material linkage (Option B from planning)
    introduction_material_id = Column(Integer, ForeignKey('materials.id'), nullable=True)  # THE material that teaches this
    
    # Mastery requirements (from planning session)
    # - 'single': One material/exercise is enough (e.g., learning fermata symbol)
    # - 'any_of_pool': Demonstrate success on any one from a pool (e.g., simple melody in 3/4)
    # - 'multiple': Must succeed on N materials (e.g., sixteenth notes in multiple contexts)
    mastery_type = Column(String, default='single')  # 'single' | 'any_of_pool' | 'multiple'
    mastery_count = Column(Integer, default=1)  # How many materials needed for 'multiple' type
    
    # Evidence profile fields (for adaptive engine)
    evidence_required_count = Column(Integer, default=1)  # How many evidence events needed for mastery
    evidence_distinct_materials = Column(Boolean, default=False)  # True = must be different materials
    evidence_acceptance_threshold = Column(Integer, default=4)  # Min rating (1-5) to count as evidence
    evidence_qualifier_json = Column(String, nullable=True)  # JSON rule filter for evidence criteria
    difficulty_weight = Column(Float, default=1.0)  # Weight for maturity calculation
    
    # Soft gate requirements (JSON: {"dimension_name": threshold_value})
    # e.g., {"interval_velocity_score": 0.5} means user must have comfortable_value >= 0.5
    # for that soft gate dimension before this capability can be mastered (hard gate, no frontier buffer)
    soft_gate_requirements = Column(String, nullable=True)
    
    # Archive/active status
    is_active = Column(Boolean, default=True)  # False = archived, not shown in normal views
    
    __table_args__ = (
        Index('ix_capability_domain', 'domain'),
        Index('ix_capability_bit_index', 'bit_index'),
    )


class MaterialCapability(Base):
    """
    Junction table linking materials to required capabilities.
    
    This replaces the comma-separated required_capability_ids field
    and enables efficient querying.
    """
    __tablename__ = 'material_capabilities'
    
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False, index=True)
    capability_id = Column(Integer, ForeignKey('capabilities.id'), nullable=False, index=True)
    
    # Whether this capability is hard-required or can be learned in context
    is_required = Column(Boolean, default=True)  # False = learnable_in_context for this material
    
    # For intervals/notes: how many occurrences in the piece
    occurrence_count = Column(Integer, default=1)
    
    __table_args__ = (
        Index('ix_material_capability_pair', 'material_id', 'capability_id', unique=True),
    )


class MaterialAnalysis(Base):
    """
    Stores extracted analysis data from MusicXML for a material.
    
    This captures computed metrics that don't fit into discrete capabilities:
    - Pitch density distribution
    - Chromatic complexity scores
    - Overall difficulty ratings
    """
    __tablename__ = 'material_analysis'
    
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False, unique=True)
    
    # Range analysis
    lowest_pitch = Column(String, nullable=True)  # e.g., "E3"
    highest_pitch = Column(String, nullable=True)  # e.g., "G5"
    range_semitones = Column(Integer, nullable=True)  # Total range in semitones
    
    # Pitch density (what % of notes fall in each zone)
    pitch_density_low = Column(Float, nullable=True)  # % in lower 33% of range
    pitch_density_mid = Column(Float, nullable=True)  # % in middle 33%
    pitch_density_high = Column(Float, nullable=True)  # % in upper 33%
    
    # For instruments with trill range concerns
    trill_lowest = Column(String, nullable=True)
    trill_highest = Column(String, nullable=True)
    
    # Complexity scores (1-10 scale)
    chromatic_complexity = Column(Float, nullable=True)  # Based on accidentals outside key
    rhythmic_complexity = Column(Float, nullable=True)  # Based on note value variety
    reading_complexity = Column(Float, nullable=True)  # Based on notation density
    
    # Tempo
    tempo_marking = Column(String, nullable=True)  # e.g., "Allegro"
    tempo_bpm = Column(Integer, nullable=True)  # If specified
    
    # Duration
    measure_count = Column(Integer, nullable=True)
    estimated_duration_seconds = Column(Integer, nullable=True)
    
    # Raw extraction data (JSON) for debugging/reanalysis
    raw_extraction_json = Column(String, nullable=True)
    
    # Staged content dimensions (for adaptive engine filtering)
    tonal_complexity_stage = Column(Integer, nullable=True)  # 0-5 stages
    interval_size_stage = Column(Integer, nullable=True)  # 0-6 stages (DEPRECATED)
    
    # NEW: Interval profile stages
    interval_sustained_stage = Column(Integer, nullable=True)  # 0-6, p75-driven, for assignment
    interval_hazard_stage = Column(Integer, nullable=True)  # 0-6, max-driven, for warnings
    legacy_interval_size_stage = Column(Integer, nullable=True)  # max(sustained, hazard) for compat
    
    # NEW: Interval profile ratios
    interval_step_ratio = Column(Float, nullable=True)  # 0-2 semitones
    interval_skip_ratio = Column(Float, nullable=True)  # 3-5 semitones
    interval_leap_ratio = Column(Float, nullable=True)  # 6-11 semitones
    interval_large_leap_ratio = Column(Float, nullable=True)  # 12-17 semitones
    interval_extreme_leap_ratio = Column(Float, nullable=True)  # 18+ semitones
    
    # NEW: Interval percentiles (semitones)
    interval_p50 = Column(Integer, nullable=True)
    interval_p75 = Column(Integer, nullable=True)
    interval_p90 = Column(Integer, nullable=True)
    
    # NEW: Interval local clustering
    interval_max_large_in_window = Column(Integer, nullable=True)
    interval_max_extreme_in_window = Column(Integer, nullable=True)
    interval_hardest_measures = Column(String, nullable=True)  # JSON array
    
    rhythm_complexity_stage = Column(Float, nullable=True)  # 0.0-1.0 continuous (global)
    rhythm_complexity_peak = Column(Float, nullable=True)  # 0.0-1.0 windowed max
    rhythm_complexity_p95 = Column(Float, nullable=True)  # 0.0-1.0 windowed 95th percentile
    range_usage_stage = Column(Integer, nullable=True)  # 0-6 stages
    melodic_predictability_stage = Column(Integer, nullable=True)  # optional later
    difficulty_index = Column(Float, nullable=True)  # 0..1 derived composite difficulty
    
    # New soft gate metrics (Phase 2)
    density_notes_per_second = Column(Float, nullable=True)  # Tempo-adjusted note density
    tempo_difficulty_score = Column(Float, nullable=True)  # 0-1 combined tempo difficulty
    interval_velocity_score = Column(Float, nullable=True)  # 0-1 IVS score (global)
    interval_velocity_peak = Column(Float, nullable=True)  # 0.0-1.0 windowed max
    interval_velocity_p95 = Column(Float, nullable=True)  # 0.0-1.0 windowed 95th percentile
    
    # Additional analysis metrics
    unique_pitch_count = Column(Integer, nullable=True)  # Distinct pitch classes (0-12)
    largest_interval_semitones = Column(Integer, nullable=True)  # Max melodic leap
    note_density_per_measure = Column(Float, nullable=True)  # Notes per measure (tempo-independent)


class UserCapability(Base):
    """
    Tracks which capabilities a user has mastered.
    """
    __tablename__ = 'user_capabilities'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    capability_id = Column(Integer, ForeignKey('capabilities.id'), nullable=False)
    
    # Learning status
    introduced_at = Column(DateTime, nullable=True)
    mastered_at = Column(DateTime, nullable=True)  # When quiz passed or demonstrated proficiency
    
    # For capabilities that can be "lost" (user reports they can no longer do something)
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    times_practiced = Column(Integer, default=0)
    times_refreshed = Column(Integer, default=0)  # Help menu access
    
    # Evidence tracking (cached from evidence events)
    evidence_count = Column(Integer, default=0)  # Cached count of qualifying evidence
    
    __table_args__ = (
        Index('ix_user_capability_pair', 'user_id', 'capability_id', unique=True),
        Index('ix_user_capability_active', 'user_id', 'is_active'),
    )


class UserComplexityScores(Base):
    """
    Stores user's demonstrated ability on continuous complexity dimensions.
    
    These are updated based on materials the user has mastered.
    """
    __tablename__ = 'user_complexity_scores'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    
    # Max demonstrated complexity (from mastered materials)
    max_chromatic_complexity = Column(Float, default=1.0)
    max_rhythmic_complexity = Column(Float, default=1.0)
    max_reading_complexity = Column(Float, default=1.0)
    
    # Comfortable complexity (average of recent successful attempts)
    comfortable_chromatic = Column(Float, default=1.0)
    comfortable_rhythmic = Column(Float, default=1.0)
    comfortable_reading = Column(Float, default=1.0)
    
    updated_at = Column(DateTime, nullable=True)


# =============================================================================
# NEW TABLES FOR ADAPTIVE PRACTICE ENGINE (v1)
# =============================================================================

class MaterialTeachesCapability(Base):
    """
    Junction table mapping materials to capabilities they TEACH (pedagogical relationship).
    
    This is separate from MaterialCapability which maps what capabilities are REQUIRED.
    'Teaches' supports:
    - Candidate generation (materialsByTeachesCapability)
    - Evidence counting (capability evidence comes from materials that teach it)
    """
    __tablename__ = 'material_teaches_capability'
    
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False, index=True)
    capability_id = Column(Integer, ForeignKey('capabilities.id'), nullable=False, index=True)
    
    # Optional metadata for debugging/analytics
    weight = Column(Float, default=1.0)  # Relative teaching importance
    notes = Column(String, nullable=True)
    
    __table_args__ = (
        Index('ix_mtc_material_capability', 'material_id', 'capability_id', unique=True),
    )


class UserMaterialState(Base):
    """
    Tracks user's mastery state and EMA for each material.
    
    Status buckets:
    - UNEXPLORED: Never attempted
    - IN_PROGRESS: Attempted but not mastered
    - MASTERED: Meets mastery threshold (EMA + min attempts)
    
    Shelf (for MASTERED materials):
    - DEFAULT: Normal rotation
    - MAINTENANCE: Included in session rotation occasionally
    - ARCHIVE: Removed from guided rotation but accessible
    """
    __tablename__ = 'user_material_state'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    
    # EMA tracking
    ema_score = Column(Float, default=0.0)  # Exponential moving average of ratings
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    
    # Status bucket
    status = Column(String, default='UNEXPLORED')  # UNEXPLORED | IN_PROGRESS | MASTERED
    
    # Shelf (meaningful when MASTERED)
    shelf = Column(String, default='DEFAULT')  # DEFAULT | MAINTENANCE | ARCHIVE
    
    # Optional: track separate guided vs manual attempts
    guided_attempt_count = Column(Integer, default=0)
    manual_attempt_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('ix_ums_user_material', 'user_id', 'material_id', unique=True),
        Index('ix_ums_user_status', 'user_id', 'status'),
        Index('ix_ums_user_shelf', 'user_id', 'shelf'),
    )


class UserPitchFocusStats(Base):
    """
    Tracks per-pitch, per-focus performance for focus targeting.
    
    Context types:
    - GLOBAL: Aggregated across all materials
    - MATERIAL: Specific to one material
    
    This enables micro-targeting inside each material by emphasizing
    the weakest pitch/focus combinations.
    """
    __tablename__ = 'user_pitch_focus_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    focus_card_id = Column(Integer, ForeignKey('focus_cards.id'), nullable=False)
    pitch_midi = Column(Integer, nullable=False)  # MIDI note number
    
    # Context
    context_type = Column(String, nullable=False)  # 'GLOBAL' | 'MATERIAL'
    context_id = Column(Integer, nullable=True)  # NULL for GLOBAL, material_id for MATERIAL
    
    # Stats
    ema_score = Column(Float, default=0.0)
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_upfs_unique', 'user_id', 'focus_card_id', 'pitch_midi', 'context_type', 'context_id', unique=True),
        Index('ix_upfs_user_context', 'user_id', 'context_type', 'context_id'),
    )


class UserCapabilityEvidenceEvent(Base):
    """
    Append-only log of evidence events for capability mastery.
    
    This is the source of truth for capability evidence counting.
    The evidence_count on UserCapability is a cached denormalization.
    
    Capabilities decide how to count evidence via their evidence profile:
    - evidence_required_count
    - evidence_distinct_materials (true/false)
    - evidence_acceptance_threshold
    - evidence_qualifier_json
    """
    __tablename__ = 'user_capability_evidence_event'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    capability_id = Column(Integer, ForeignKey('capabilities.id'), nullable=False)
    
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=True)  # Nullable (some evidence may not be material-specific)
    practice_attempt_id = Column(Integer, ForeignKey('practice_attempts.id'), nullable=True)
    
    rating = Column(Integer, nullable=True)
    credited_at = Column(DateTime, nullable=False)
    
    is_off_course = Column(Boolean, default=False)  # True = from manual/off-course practice
    
    __table_args__ = (
        Index('ix_ucee_user_cap', 'user_id', 'capability_id'),
        Index('ix_ucee_user_cap_material', 'user_id', 'capability_id', 'material_id'),
    )


class Collection(Base):
    """
    Represents a collection/group of materials (e.g., etude book, excerpt list).
    
    Used to show progress like "Etude Book A: 10/14 unlocked"
    """
    __tablename__ = 'collections'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)  # e.g., "EtudeBooks", "Solos", "Excerpts"
    source_type = Column(String, nullable=True)  # public | licensed | user
    license_id = Column(Integer, ForeignKey('licenses.id'), nullable=True)
    metadata_json = Column(String, nullable=True)  # JSON for additional attributes


class CollectionMaterial(Base):
    """Junction table linking collections to materials with ordering."""
    __tablename__ = 'collection_materials'
    
    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey('collections.id'), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False, index=True)
    order_index = Column(Integer, nullable=True)  # Position within collection
    
    __table_args__ = (
        Index('ix_cm_collection_material', 'collection_id', 'material_id', unique=True),
    )


class License(Base):
    """
    Represents a content license/access grant.
    
    Minimal scaffolding for future monetization.
    """
    __tablename__ = 'licenses'
    
    id = Column(Integer, primary_key=True)
    license_type = Column(String, nullable=True)  # public_domain | licensed_book | subscription_pack
    provider = Column(String, nullable=True)
    metadata_json = Column(String, nullable=True)  # JSON


class UserLicense(Base):
    """Tracks which licenses a user has access to."""
    __tablename__ = 'user_licenses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    license_id = Column(Integer, ForeignKey('licenses.id'), nullable=False)
    purchased_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_ul_user_license', 'user_id', 'license_id', unique=True),
    )


# =============================================================================
# SOFT GATE SYSTEM
# =============================================================================

class SoftGateRule(Base):
    """
    Configuration table for soft-gate dimension rules.
    
    Each row defines how one continuous dimension (e.g., rhythm_complexity_stage)
    should be gated and how promotion occurs.
    
    Soft gates differ from hard capabilities:
    - Hard capability: Binary (you have it or not)
    - Soft gate: Continuous, with comfort zone + frontier buffer
    
    Promotion logic (EMA-based):
    - Only update EMA when attempt is in-band (<= comfort + frontier_buffer)
    - Only count as frontier attempt if value > comfort
    - Promote when: frontier_attempt_count >= min_attempts AND ema >= threshold
    """
    __tablename__ = 'soft_gate_rules'
    
    id = Column(Integer, primary_key=True)
    dimension_name = Column(String, unique=True, nullable=False)  # e.g., "tonal_complexity_stage"
    
    # How far above comfort guided sessions may go
    frontier_buffer = Column(Float, nullable=False)  # e.g., 1.0 (can select comfort+1)
    
    # How much to increase comfort on promotion
    promotion_step = Column(Float, nullable=False)  # e.g., 1.0
    
    # Minimum frontier attempts before promotion possible
    min_attempts = Column(Integer, nullable=False)  # e.g., 10
    
    # What rating counts as success
    success_rating_threshold = Column(Integer, default=4)  # 1-5 scale
    
    # How many successes needed (for window-based logic)
    success_required_count = Column(Integer, nullable=False)  # e.g., 8
    
    # Window size for "X of last Y" logic (optional)
    success_window_count = Column(Integer, nullable=True)  # e.g., 12 for "8 of last 12"
    
    # Decay halflife for recency weighting (optional)
    decay_halflife_days = Column(Float, nullable=True)


class UserSoftGateState(Base):
    """
    Tracks user's soft-gate state per dimension using EMA.
    
    EMA update formula:
        success_event = 1 if rating >= threshold else 0
        ema = alpha * success_event + (1 - alpha) * ema
    
    Where alpha ~ 0.10 gives behavior like "last ~10 attempts".
    
    Promotion conditions:
        - frontier_attempt_count_since_last_promo >= min_attempts
        - frontier_success_ema >= 0.75 (or configured threshold)
    
    On promotion:
        - comfortable_value += promotion_step
        - frontier_attempt_count_since_last_promo = 0
        - optionally: frontier_success_ema *= 0.9 (prevents instant double-promote)
    """
    __tablename__ = 'user_soft_gate_state'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    dimension_name = Column(String, nullable=False)  # e.g., "tonal_complexity_stage"
    
    # Current comfort zone
    comfortable_value = Column(Float, nullable=False, default=0.0)
    
    # Highest value ever demonstrated successfully
    max_demonstrated_value = Column(Float, nullable=False, default=0.0)
    
    # EMA of frontier success (0-1)
    frontier_success_ema = Column(Float, nullable=False, default=0.0)
    
    # Attempts in frontier zone since last promotion
    frontier_attempt_count_since_last_promo = Column(Integer, nullable=False, default=0)
    
    # Last update time
    updated_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_usgs_user_dimension', 'user_id', 'dimension_name', unique=True),
        Index('ix_usgs_user', 'user_id'),
    )


# =============================================================================
# BITMASK COLUMNS (to be added to existing tables via migration)
# =============================================================================
# 
# Users table additions:
#   cap_mask_0 BIGINT DEFAULT 0  -- capabilities 0-63
#   cap_mask_1 BIGINT DEFAULT 0  -- capabilities 64-127
#   cap_mask_2 BIGINT DEFAULT 0  -- capabilities 128-191
#   cap_mask_3 BIGINT DEFAULT 0  -- capabilities 192-255
#   cap_mask_4 BIGINT DEFAULT 0  -- capabilities 256-319
#   cap_mask_5 BIGINT DEFAULT 0  -- capabilities 320-383
#   cap_mask_6 BIGINT DEFAULT 0  -- capabilities 384-447
#   cap_mask_7 BIGINT DEFAULT 0  -- capabilities 448-511
#
# Materials table additions:
#   req_cap_mask_0 BIGINT DEFAULT 0  -- required capabilities 0-63
#   req_cap_mask_1 BIGINT DEFAULT 0  -- etc.
#   ... (same pattern)
#
# Query for eligible materials:
#   SELECT * FROM materials m
#   WHERE (m.req_cap_mask_0 & ~u.cap_mask_0) = 0
#     AND (m.req_cap_mask_1 & ~u.cap_mask_1) = 0
#     AND ... (for all 8 masks)
#
# This returns materials where every required bit is set in user's mask.
# =============================================================================
