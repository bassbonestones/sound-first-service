"""
MusicXML Extractor

Main analyzer class for extracting capabilities and metrics from MusicXML files.
Orchestrates extraction through focused parser modules.
"""

from typing import Any, List, Tuple

try:
    from music21 import converter
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

# Export MUSIC21_AVAILABLE for tests and conditional imports
__all__ = ['MUSIC21_AVAILABLE', 'MusicXMLAnalyzer', 'analyze_musicxml', 
           'compute_capability_bitmask', 'check_eligibility']

from .extraction_models import ExtractionResult

# Import parser modules
from .note_parser import extract_notes_and_rests
from .interval_parser import extract_intervals
from .notation_parser import (
    extract_metadata, extract_clefs, extract_time_signatures,
    extract_key_signatures, extract_dynamics, extract_articulations,
    extract_ornaments, extract_tempo_expression, extract_repeats,
    extract_other_notation,
)
from .pattern_analyzer import analyze_rhythm_patterns, analyze_melodic_patterns
from .range_analyzer import analyze_range, analyze_chromatic_complexity
from .capability_mapper import get_capability_names as _get_capability_names


class MusicXMLAnalyzer:
    """
    Analyzes MusicXML files to extract capabilities and metrics.
    
    Usage:
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(musicxml_string)
        capabilities = analyzer.get_capability_names(result)
    """
    
    def __init__(self) -> None:
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is required for MusicXML analysis")
    
    def analyze(self, musicxml_content: str) -> ExtractionResult:
        """
        Analyze MusicXML content and extract all capabilities.
        
        Args:
            musicxml_content: MusicXML string
            
        Returns:
            ExtractionResult with all extracted information
        """
        result = ExtractionResult()
        
        # Parse the MusicXML
        try:
            score: Any = converter.parse(musicxml_content)
        except Exception as e:
            raise ValueError(f"Failed to parse MusicXML: {e}")
        
        # Extract basic notation elements
        extract_metadata(score, result)
        extract_clefs(score, result)
        extract_time_signatures(score, result)
        extract_key_signatures(score, result)
        
        # Extract notes, rests, and intervals
        extract_notes_and_rests(score, result)
        extract_intervals(score, result)
        
        # Extract expressive elements
        extract_dynamics(score, result)
        extract_articulations(score, result)
        extract_ornaments(score, result)
        extract_tempo_expression(score, result)
        
        # Extract structural elements
        extract_repeats(score, result)
        extract_other_notation(score, result)
        
        # Analyze patterns and ranges
        analyze_range(score, result)
        analyze_chromatic_complexity(score, result)
        analyze_rhythm_patterns(score, result)
        analyze_melodic_patterns(score, result)
        
        # Count measures
        result.measure_count = len(score.parts[0].getElementsByClass('Measure')) if score.parts else 0
        
        return result
    
    def get_capability_names(self, result: ExtractionResult) -> List[str]:
        """
        Convert extraction result to list of capability names.
        
        Returns:
            List of capability ID names (e.g., ["clef_treble", "time_sig_4_4", ...])
        """
        return _get_capability_names(result)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def analyze_musicxml(musicxml_content: str) -> Tuple[ExtractionResult, List[str]]:
    """
    Convenience function to analyze MusicXML and get capabilities.
    
    Returns:
        Tuple of (ExtractionResult, list of capability names)
    """
    analyzer = MusicXMLAnalyzer()
    result: ExtractionResult = analyzer.analyze(musicxml_content)
    capabilities: List[str] = analyzer.get_capability_names(result)
    return result, capabilities


def compute_capability_bitmask(capability_ids: List[int]) -> List[int]:
    """
    Compute bitmask values for a list of capability IDs.
    
    Args:
        capability_ids: List of capability IDs (each has a bit_index 0-511)
        
    Returns:
        List of 8 integers representing the 8 mask columns
    """
    masks = [0] * 8
    for cap_id in capability_ids:
        bucket = cap_id // 64
        bit_position = cap_id % 64
        if 0 <= bucket < 8:
            masks[bucket] |= (1 << bit_position)
    return masks


def check_eligibility(user_masks: List[int], material_masks: List[int]) -> bool:
    """
    Check if a user is eligible for a material using bitmasks.
    
    Args:
        user_masks: User's 8 capability mask values
        material_masks: Material's 8 required capability mask values
        
    Returns:
        True if user has all required capabilities
    """
    for i in range(8):
        user_mask = user_masks[i] or 0
        material_mask = material_masks[i] or 0
        # User must have all bits that material requires
        if (material_mask & ~user_mask) != 0:
            return False
    return True
