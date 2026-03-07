"""
Analyzers Package

MusicXML analysis modules for capability extraction and metrics calculation.

Main Classes:
    MusicXMLAnalyzer: Main analyzer for extracting capabilities from MusicXML

Data Classes:
    ExtractionResult: Complete extraction result
    IntervalInfo: Interval occurrence info
    RangeAnalysis: Pitch range with density analysis
    RhythmPatternAnalysis: Sight-reading difficulty predictor
    MelodicPatternAnalysis: Phase 8 predictability scoring

Utility Functions:
    analyze_musicxml: Convenience function for analysis
    compute_capability_bitmask: Convert capability IDs to bitmask
    check_eligibility: Check user eligibility for material

Capability Maps:
    CLEF_CAPABILITY_MAP, NOTE_VALUE_CAPABILITY_MAP, REST_CAPABILITY_MAP,
    DYNAMIC_CAPABILITY_MAP, ARTICULATION_CAPABILITY_MAP, ORNAMENT_CAPABILITY_MAP,
    TEMPO_TERMS, EXPRESSION_TERMS
"""

# Data classes
from .extraction_models import (
    ExtractionResult,
    IntervalInfo,
    RangeAnalysis,
    RhythmPatternAnalysis,
    MelodicPatternAnalysis,
    format_pitch_name,
)

# Capability maps
from .capability_maps import (
    CLEF_CAPABILITY_MAP,
    NOTE_VALUE_CAPABILITY_MAP,
    REST_CAPABILITY_MAP,
    DYNAMIC_CAPABILITY_MAP,
    ARTICULATION_CAPABILITY_MAP,
    ORNAMENT_CAPABILITY_MAP,
    TEMPO_TERMS,
    EXPRESSION_TERMS,
)

# Main analyzer class and utility functions
from .extractor import (
    MUSIC21_AVAILABLE,
    MusicXMLAnalyzer,
    analyze_musicxml,
    compute_capability_bitmask,
    check_eligibility,
)

__all__ = [
    # Data classes
    'ExtractionResult',
    'IntervalInfo',
    'RangeAnalysis',
    'RhythmPatternAnalysis',
    'MelodicPatternAnalysis',
    'format_pitch_name',
    # Capability maps
    'CLEF_CAPABILITY_MAP',
    'NOTE_VALUE_CAPABILITY_MAP',
    'REST_CAPABILITY_MAP',
    'DYNAMIC_CAPABILITY_MAP',
    'ARTICULATION_CAPABILITY_MAP',
    'ORNAMENT_CAPABILITY_MAP',
    'TEMPO_TERMS',
    'EXPRESSION_TERMS',
    # Analyzer and utilities
    'MUSIC21_AVAILABLE',
    'MusicXMLAnalyzer',
    'analyze_musicxml',
    'compute_capability_bitmask',
    'check_eligibility',
]
