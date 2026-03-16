"""
Capability Mapper

Convert ExtractionResult to list of capability names.
"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .extraction_models import ExtractionResult


def get_capability_names(result: "ExtractionResult") -> List[str]:
    """
    Convert extraction result to list of capability names.
    
    Returns:
        List of capability ID names (e.g., ["clef_treble", "time_sig_4_4", ...])
    """
    capabilities: List[str] = []
    
    # Clefs
    capabilities.extend(result.clefs)
    
    # Time signatures
    capabilities.extend(result.time_signatures)
    
    # Key signatures
    capabilities.extend(result.key_signatures)
    
    # Note values
    capabilities.extend(result.note_values.keys())
    
    # Dotted notes
    for dn in result.dotted_notes:
        capabilities.append(f"note_{dn}")
    
    # Ties
    if result.has_ties:
        capabilities.append("notation_ties")
    
    # Rests
    capabilities.extend(result.rest_values.keys())
    
    # Multi-measure rests
    if result.has_multi_measure_rest:
        capabilities.append("rest_multi_measure")
    
    # Tuplets
    capabilities.extend(result.tuplets.keys())
    
    # Melodic intervals
    for key_name in result.melodic_intervals.keys():
        capabilities.append(key_name)
    
    # Harmonic intervals
    for key_name in result.harmonic_intervals.keys():
        capabilities.append(key_name)
    
    # Dynamics
    capabilities.extend(result.dynamics)
    
    # Dynamic changes
    capabilities.extend(result.dynamic_changes)
    
    # Articulations
    capabilities.extend(result.articulations)
    
    # Ornaments
    capabilities.extend(result.ornaments)
    
    # Tempo markings
    capabilities.extend(result.tempo_markings)
    
    # Expression terms
    capabilities.extend(result.expression_terms)
    
    # Repeat structures
    capabilities.extend(result.repeat_structures)
    
    # Fermatas
    if result.fermatas > 0:
        capabilities.append("notation_fermata")
    
    # Breath marks
    if result.breath_marks > 0:
        capabilities.append("notation_breath_mark")
    
    # Chord symbols
    if result.chord_symbols:
        capabilities.append("notation_chord_symbols")
    
    # Figured bass
    if result.figured_bass:
        capabilities.append("notation_figured_bass")
    
    # Multi-voice
    if result.max_voices >= 2:
        capabilities.append(f"notation_{result.max_voices}_voices")
    
    return capabilities
