"""
MusicXML Analyzer for Sound First

FACADE MODULE - Re-exports from app.analyzers package.

This file maintains backward compatibility for existing imports.
The actual implementation is in app/analyzers/.
"""

# Re-export everything from the analyzers package
from app.analyzers import (
    # Data classes
    ExtractionResult,
    IntervalInfo,
    RangeAnalysis,
    RhythmPatternAnalysis,
    MelodicPatternAnalysis,
    format_pitch_name,
    # Capability maps
    CLEF_CAPABILITY_MAP,
    NOTE_VALUE_CAPABILITY_MAP,
    REST_CAPABILITY_MAP,
    DYNAMIC_CAPABILITY_MAP,
    ARTICULATION_CAPABILITY_MAP,
    ORNAMENT_CAPABILITY_MAP,
    TEMPO_TERMS,
    EXPRESSION_TERMS,
    # Analyzer and utilities
    MUSIC21_AVAILABLE,
    MusicXMLAnalyzer,
    analyze_musicxml,
    compute_capability_bitmask,
    check_eligibility,
)

