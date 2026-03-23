"""
Element Mappings and Matchers

Maps music21 class names to extraction result fields and handles element detection.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# Clef mappings: music21 class name -> ExtractionResult clef name
CLEF_MAP = {
    "music21.clef.TrebleClef": "clef_treble",
    "music21.clef.BassClef": "clef_bass",
    "music21.clef.AltoClef": "clef_alto",
    "music21.clef.TenorClef": "clef_tenor",
    "music21.clef.Treble8vbClef": "clef_treble_8vb",
    "music21.clef.Bass8vaClef": "clef_bass_8va",
}

# Articulation mappings
ARTICULATION_MAP = {
    "music21.articulations.Staccato": "articulation_staccato",
    "music21.articulations.Staccatissimo": "articulation_staccatissimo",
    "music21.articulations.Accent": "articulation_accent",
    "music21.articulations.StrongAccent": "articulation_marcato",
    "music21.articulations.Tenuto": "articulation_tenuto",
    "music21.articulations.DetachedLegato": "articulation_portato",
    "music21.articulations.BreathMark": "notation_breath_mark",
}

# Ornament mappings
ORNAMENT_MAP = {
    "music21.expressions.Trill": "ornament_trill",
    "music21.expressions.Mordent": "ornament_mordent",
    "music21.expressions.InvertedMordent": "ornament_inverted_mordent",
    "music21.expressions.Turn": "ornament_turn",
    "music21.expressions.InvertedTurn": "ornament_inverted_turn",
    "music21.expressions.Tremolo": "ornament_tremolo",
}


def check_element(config: Dict[str, Any], result: Any, score: Any = None) -> bool:
    """Check for music21 element class presence."""
    class_name = config.get("class", "")
    
    # Clefs
    if class_name in CLEF_MAP:
        return CLEF_MAP[class_name] in result.clefs
    
    # Articulations
    if class_name in ARTICULATION_MAP:
        mapped = ARTICULATION_MAP[class_name]
        if mapped in result.articulations:
            return True
        # Also check for breath marks specifically
        if mapped == "notation_breath_mark" and result.breath_marks > 0:
            return True
        return False
    
    # Ornaments
    if class_name in ORNAMENT_MAP:
        return ORNAMENT_MAP[class_name] in result.ornaments
    
    # Fermata
    if class_name == "music21.expressions.Fermata":
        return bool(result.fermatas > 0)
    
    # Spanners and dynamics that require score access
    if score is not None:
        return _check_score_elements(class_name, result, score)
    
    logger.debug(f"Unknown element class: {class_name}")
    return False


def _check_score_elements(class_name: str, result: Any, score: Any) -> bool:
    """Check elements that require score traversal."""
    try:
        # Slurs for legato - also check result.articulations for text-based legato
        if class_name == "music21.spanner.Slur":
            # First check if "articulation_legato" was detected via text direction
            if "articulation_legato" in result.articulations:
                return True
            # Then check for actual slur elements
            from music21 import spanner
            for sp in score.recurse().getElementsByClass(spanner.Slur):
                return True
            return False
        
        # Glissando
        if class_name == "music21.spanner.Glissando":
            from music21 import spanner
            for sp in score.recurse().getElementsByClass(spanner.Glissando):
                return True
            return False
        
        # Crescendo / Decrescendo / Diminuendo
        if class_name == "music21.dynamics.Crescendo":
            from music21 import dynamics, spanner
            for d in score.recurse().getElementsByClass(dynamics.Crescendo):
                return True
            for sp in score.recurse().getElementsByClass(spanner.Spanner):
                if hasattr(sp, 'type') and sp.type == 'crescendo':
                    return True
            return "crescendo" in str(result.dynamic_changes).lower()
        
        if class_name == "music21.dynamics.Decrescendo":
            from music21 import dynamics, spanner
            for d in score.recurse().getElementsByClass(dynamics.Diminuendo):
                return True
            for sp in score.recurse().getElementsByClass(spanner.Spanner):
                if hasattr(sp, 'type') and sp.type == 'decrescendo':
                    return True
            return "decrescendo" in str(result.dynamic_changes).lower()
        
        if class_name == "music21.dynamics.Diminuendo":
            from music21 import dynamics
            for d in score.recurse().getElementsByClass(dynamics.Diminuendo):
                return True
            return "diminuendo" in str(result.dynamic_changes).lower()
            
    except Exception as e:
        logger.debug(f"Error checking element {class_name}: {e}")
    
    return False
