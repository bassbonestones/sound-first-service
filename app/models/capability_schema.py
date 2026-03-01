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


class CapabilityV2(Base):
    """
    Enhanced capability model with prerequisites and bitmask support.
    
    The bit_index field maps this capability to a specific bit position
    for fast eligibility checking. Capabilities 0-63 go in cap_mask_0,
    64-127 in cap_mask_1, etc.
    """
    __tablename__ = 'capabilities_v2'
    
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
    sequence_order = Column(Integer, nullable=True)  # Suggested introduction order
    explanation = Column(String, nullable=True)  # Teaching text
    visual_example_url = Column(String, nullable=True)
    audio_example_url = Column(String, nullable=True)
    
    # Quiz
    quiz_type = Column(String, nullable=True)
    quiz_question = Column(String, nullable=True)
    quiz_options = Column(String, nullable=True)  # JSON
    quiz_answer = Column(String, nullable=True)
    
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
    capability_id = Column(Integer, ForeignKey('capabilities_v2.id'), nullable=False, index=True)
    
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


class UserCapabilityV2(Base):
    """
    Tracks which capabilities a user has mastered.
    """
    __tablename__ = 'user_capabilities_v2'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    capability_id = Column(Integer, ForeignKey('capabilities_v2.id'), nullable=False)
    
    # Learning status
    introduced_at = Column(DateTime, nullable=True)
    mastered_at = Column(DateTime, nullable=True)  # When quiz passed or demonstrated proficiency
    
    # For capabilities that can be "lost" (user reports they can no longer do something)
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    times_practiced = Column(Integer, default=0)
    times_refreshed = Column(Integer, default=0)  # Help menu access
    
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
