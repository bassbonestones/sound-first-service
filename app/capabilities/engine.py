"""
Detection Engine for capability detection.

Applies detection rules to MusicXML extraction results to identify
which capabilities are present in a given piece of music.
"""

import logging
from typing import Any, Dict, List, Set

from .types import DetectionRule, DetectionType
from .registry import CapabilityRegistry
from .custom_detectors import CUSTOM_DETECTORS

logger = logging.getLogger(__name__)


class DetectionEngine:
    """
    Engine for detecting capabilities in MusicXML extraction results.
    """
    
    def __init__(self, registry: CapabilityRegistry):
        """
        Initialize with a capability registry.
        
        Args:
            registry: CapabilityRegistry with loaded detection rules
        """
        self.registry = registry
    
    def detect_capabilities(
        self,
        extraction_result,  # ExtractionResult from musicxml_analyzer
        score=None,  # Optional music21 score for custom detectors
    ) -> Set[str]:
        """
        Detect all capabilities present in the extraction result.
        
        Args:
            extraction_result: ExtractionResult from MusicXMLAnalyzer
            score: Optional music21 Score for custom detection functions
            
        Returns:
            Set of detected capability names
        """
        detected = set()
        
        for name, rule in self.registry.rules.items():
            if not rule.is_valid or rule.detection_type is None:
                continue
            
            try:
                if self._check_rule(rule, extraction_result, score):
                    detected.add(name)
            except Exception as e:
                logger.warning(f"Error checking rule for '{name}': {e}")
        
        return detected
    
    def _check_rule(
        self,
        rule: DetectionRule,
        result,  # ExtractionResult
        score,
    ) -> bool:
        """Check if a single detection rule matches."""
        
        if rule.detection_type == DetectionType.ELEMENT:
            return self._check_element(rule.config, result, score)
        
        elif rule.detection_type == DetectionType.VALUE_MATCH:
            return self._check_value_match(rule.config, result)
        
        elif rule.detection_type == DetectionType.COMPOUND:
            return self._check_compound(rule.config, result)
        
        elif rule.detection_type == DetectionType.INTERVAL:
            return self._check_interval(rule.config, result)
        
        elif rule.detection_type == DetectionType.TEXT_MATCH:
            return self._check_text_match(rule.config, result)
        
        elif rule.detection_type == DetectionType.TIME_SIGNATURE:
            return self._check_time_signature(rule.config, result)
        
        elif rule.detection_type == DetectionType.RANGE:
            return self._check_range(rule.config, result)
        
        elif rule.detection_type == DetectionType.CUSTOM:
            return self._check_custom(rule.config, result, score)
        
        return False
    
    def _check_element(self, config: Dict, result, score=None) -> bool:
        """Check for music21 element class presence."""
        class_name = config.get("class", "")
        
        # Map class names to ExtractionResult fields
        # e.g., "music21.clef.TrebleClef" -> check if "clef_treble" in result.clefs
        
        # Clefs
        clef_map = {
            "music21.clef.TrebleClef": "clef_treble",
            "music21.clef.BassClef": "clef_bass",
            "music21.clef.AltoClef": "clef_alto",
            "music21.clef.TenorClef": "clef_tenor",
            "music21.clef.Treble8vbClef": "clef_treble_8vb",
            "music21.clef.Bass8vaClef": "clef_bass_8va",
        }
        if class_name in clef_map:
            return clef_map[class_name] in result.clefs
        
        # Articulations
        articulation_map = {
            "music21.articulations.Staccato": "articulation_staccato",
            "music21.articulations.Staccatissimo": "articulation_staccatissimo",
            "music21.articulations.Accent": "articulation_accent",
            "music21.articulations.StrongAccent": "articulation_marcato",
            "music21.articulations.Tenuto": "articulation_tenuto",
            "music21.articulations.DetachedLegato": "articulation_portato",
            "music21.articulations.BreathMark": "notation_breath_mark",
        }
        if class_name in articulation_map:
            mapped = articulation_map[class_name]
            if mapped in result.articulations:
                return True
            # Also check for breath marks specifically
            if mapped == "notation_breath_mark" and result.breath_marks > 0:
                return True
            return False
        
        # Ornaments
        ornament_map = {
            "music21.expressions.Trill": "ornament_trill",
            "music21.expressions.Mordent": "ornament_mordent",
            "music21.expressions.InvertedMordent": "ornament_inverted_mordent",
            "music21.expressions.Turn": "ornament_turn",
            "music21.expressions.InvertedTurn": "ornament_inverted_turn",
            "music21.expressions.Tremolo": "ornament_tremolo",
        }
        if class_name in ornament_map:
            return ornament_map[class_name] in result.ornaments
        
        # Other symbols
        if class_name == "music21.expressions.Fermata":
            return result.fermatas > 0
        
        # Spanners and dynamics that require score access
        if score is not None:
            try:
                # Slurs for legato
                if class_name == "music21.spanner.Slur":
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
                    from music21 import dynamics
                    for d in score.recurse().getElementsByClass(dynamics.Crescendo):
                        return True
                    # Also check for wedges/hairpins
                    from music21 import spanner
                    for sp in score.recurse().getElementsByClass(spanner.Spanner):
                        if hasattr(sp, 'type') and sp.type == 'crescendo':
                            return True
                    return "crescendo" in str(result.dynamic_changes).lower()
                
                if class_name == "music21.dynamics.Decrescendo":
                    from music21 import dynamics
                    for d in score.recurse().getElementsByClass(dynamics.Decrescendo):
                        return True
                    from music21 import spanner
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
        
        logger.debug(f"Unknown element class: {class_name}")
        return False
    
    def _check_value_match(self, config: Dict, result) -> bool:
        """Check for field value match on source objects."""
        source = config.get("source")
        field_path = config.get("field", "")
        
        # Get the source data from ExtractionResult
        source_data = self._get_source_data(source, result)
        if not source_data:
            return False
        
        # Check each item
        for item in source_data:
            if self._check_value_condition(item, field_path, config):
                return True
        
        return False
    
    def _check_compound(self, config: Dict, result) -> bool:
        """Check multiple conditions (AND logic)."""
        source = config.get("source")
        conditions = config.get("conditions", [])
        
        source_data = self._get_source_data(source, result)
        if not source_data:
            return False
        
        # An item must satisfy ALL conditions
        for item in source_data:
            all_match = True
            for cond in conditions:
                field_path = cond.get("field", "")
                if not self._check_value_condition(item, field_path, cond):
                    all_match = False
                    break
            if all_match:
                return True
        
        return False
    
    def _check_interval(self, config: Dict, result) -> bool:
        """Check for interval quality/direction."""
        quality = config.get("quality")  # e.g., "M3", "P5"
        melodic = config.get("melodic", True)
        direction = config.get("direction")  # "ascending", "descending", or None (any)
        
        intervals = result.melodic_intervals if melodic else result.harmonic_intervals
        
        for key, info in intervals.items():
            if info.name == quality:
                if direction is None or info.direction == direction:
                    return True
        
        return False
    
    def _check_text_match(self, config: Dict, result) -> bool:
        """Check for text content in expressions/tempos."""
        source = config.get("source")
        contains = config.get("contains", "").lower()
        equals = config.get("equals", "").lower()
        
        # Get text items based on source
        if source in ("tempos", "tempo_markings"):
            texts = result.tempo_markings
        elif source in ("expressions", "expression_terms"):
            texts = result.expression_terms
        elif source == "dynamics":
            texts = result.dynamics
        else:
            return False
        
        # For expression_terms, items are stored as capability names like "expression_con_brio"
        # So we also need to check the underscore-converted form
        contains_underscore = contains.replace(" ", "_")
        equals_underscore = equals.replace(" ", "_")
        
        for text in texts:
            text_lower = text.lower()
            if equals and text_lower == equals:
                return True
            if contains and contains in text_lower:
                return True
            # Also check with underscore conversion for capability-style names
            if equals_underscore and equals_underscore in text_lower:
                return True
            if contains_underscore and contains_underscore in text_lower:
                return True
        
        return False
    
    def _check_time_signature(self, config: Dict, result) -> bool:
        """Check for time signature match."""
        numerator = config.get("numerator")
        denominator = config.get("denominator")
        
        expected = f"time_sig_{numerator}_{denominator}"
        return expected in result.time_signatures
    
    def _check_range(self, config: Dict, result) -> bool:
        """Check for interval size range."""
        min_semi = config.get("min_semitones", 0)
        max_semi = config.get("max_semitones", 999)
        
        if not result.range_analysis:
            return False
        
        range_semi = result.range_analysis.range_semitones
        return min_semi <= range_semi <= max_semi
    
    def _check_custom(self, config: Dict, result, score) -> bool:
        """Execute custom detection function."""
        func_name = config.get("function")
        if func_name not in CUSTOM_DETECTORS:
            return False
        
        return CUSTOM_DETECTORS[func_name](result, score)
    
    def _get_source_data(self, source: str, result) -> List[Any]:
        """Get source data from ExtractionResult as a list of items."""
        # For value_match/compound, we need to return pseudo-items
        # that can have their fields checked
        
        # Map internal note type names to match detection rule conventions
        # Note: music21 uses "16th" but rules might use "sixteenth"
        # We normalize to match what the detection rules expect
        NOTE_TYPE_MAP = {
            "thirty_second": "32nd",
            "sixty_fourth": "64th",
            "16th": "sixteenth",  # music21 uses "16th", rules use "sixteenth"
        }
        
        if source == "notes":
            # Return note value info as pseudo-objects
            items = []
            for note_type, count in result.note_values.items():
                clean_type = note_type.replace("note_", "")
                # Normalize to match detection rule naming convention
                normalized = NOTE_TYPE_MAP.get(clean_type, clean_type)
                items.append({"type": normalized, "count": count, "dots": 0})
            # Add dotted notes - provide BOTH formats to support different rule styles:
            # 1. Rules using type: "dotted_half" (basic dotted rhythm detection)
            # 2. Rules using type: "half" + dots >= 1 (compound conditions)
            for dotted in result.dotted_notes:
                # Add full name format (e.g., "dotted_half", "double_dotted_half")
                # Normalize 16th -> sixteenth in full name too
                full_name = dotted
                for old, new in [("16th", "sixteenth"), ("32nd", "thirty_second")]:
                    full_name = full_name.replace(old, new)
                items.append({"type": full_name, "dots": 1 if "double" not in dotted else 2})
                
                # Also add parsed format (e.g., type: "half", dots: 1)
                if dotted.startswith("double_dotted_"):
                    base_type = dotted.replace("double_dotted_", "")
                    normalized_base = NOTE_TYPE_MAP.get(base_type, base_type)
                    items.append({"type": normalized_base, "dots": 2})
                elif dotted.startswith("dotted_"):
                    base_type = dotted.replace("dotted_", "")
                    normalized_base = NOTE_TYPE_MAP.get(base_type, base_type)
                    items.append({"type": normalized_base, "dots": 1})
            return items
        
        elif source == "dynamics":
            return [{"value": d.replace("dynamic_", "")} for d in result.dynamics]
        
        elif source == "rests":
            items = []
            for rest_type, count in result.rest_values.items():
                clean_type = rest_type.replace("rest_", "")
                normalized = NOTE_TYPE_MAP.get(clean_type, clean_type)
                items.append({"type": normalized, "count": count})
            return items
        
        elif source == "articulations":
            return [{"name": a.replace("articulation_", "")} for a in result.articulations]
        
        elif source == "ornaments":
            return [{"name": o.replace("ornament_", "")} for o in result.ornaments]
        
        elif source == "clefs":
            return [{"name": c.replace("clef_", "")} for c in result.clefs]
        
        elif source == "time_signatures":
            items = []
            for ts in result.time_signatures:
                # Parse "time_sig_4_4" -> {"numerator": 4, "denominator": 4}
                parts = ts.replace("time_sig_", "").split("_")
                if len(parts) == 2:
                    items.append({"numerator": int(parts[0]), "denominator": int(parts[1])})
            return items
        
        elif source == "key_signatures":
            return [{"name": k} for k in result.key_signatures]
        
        elif source == "intervals":
            items = []
            for key, info in result.melodic_intervals.items():
                items.append({
                    "name": info.name,
                    "direction": info.direction,
                    "semitones": info.semitones,
                    "quality": info.quality,
                    "is_melodic": True,
                })
            for key, info in result.harmonic_intervals.items():
                items.append({
                    "name": info.name,
                    "semitones": info.semitones,
                    "quality": info.quality,
                    "is_melodic": False,
                })
            return items
        
        return []
    
    def _check_value_condition(self, item: Any, field_path: str, config: Dict) -> bool:
        """Check a single value condition against an item."""
        # Get the value from the item using dot-notation field path
        value = self._get_nested_value(item, field_path)
        
        if value is None:
            return False
        
        # Check conditions
        if "eq" in config:
            return value == config["eq"]
        if "contains" in config:
            return config["contains"].lower() in str(value).lower()
        if "gte" in config:
            return value >= config["gte"]
        if "lte" in config:
            return value <= config["lte"]
        
        return False
    
    def _get_nested_value(self, item: Any, field_path: str) -> Any:
        """Get value from item using dot-notation path."""
        if not field_path:
            return item
        
        parts = field_path.split(".")
        current = item
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            
            if current is None:
                return None
        
        return current
