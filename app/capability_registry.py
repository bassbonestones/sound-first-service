"""
Capability Registry for Sound First

Manages capability detection rules loaded from capabilities.json.
Validates rules at startup and provides a detection engine that
applies rules to MusicXML extraction results.

Detection Types:
- element: Direct music21 class presence check
- value_match: Field comparison on source objects
- compound: Multiple conditions (AND logic)
- interval: Melodic/harmonic interval detection
- text_match: TextExpression content matching
- time_signature: Time signature numerator/denominator match
- range: Interval size range check
- custom: Python function fallback
- null: Not auto-detectable (foundational capabilities)
"""

import json
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# DETECTION TYPES ENUM
# =============================================================================

class DetectionType(str, Enum):
    ELEMENT = "element"
    VALUE_MATCH = "value_match"
    COMPOUND = "compound"
    INTERVAL = "interval"
    TEXT_MATCH = "text_match"
    TIME_SIGNATURE = "time_signature"
    RANGE = "range"
    CUSTOM = "custom"


# =============================================================================
# DETECTION RULE SCHEMA
# =============================================================================

@dataclass
class DetectionRule:
    """Validated detection rule for a capability."""
    capability_name: str
    detection_type: Optional[DetectionType]
    config: Dict[str, Any]
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


# =============================================================================
# VALID SOURCES FOR VALUE_MATCH, COMPOUND, TEXT_MATCH
# =============================================================================

VALID_SOURCES = {
    "notes",
    "dynamics", 
    "tempos",
    "expressions",
    "articulations",
    "clefs",
    "key_signatures",
    "time_signatures",
    "intervals",
    "ornaments",
    "rests",
}


# =============================================================================
# REGISTRY FOR CUSTOM DETECTION FUNCTIONS
# =============================================================================

# Custom detection functions are registered here
# Each function takes (extraction_result, score) and returns bool
CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


# Example custom detectors (can be expanded)
@register_custom_detector("detect_syncopation")
def detect_syncopation(extraction_result, score) -> bool:
    """Detect syncopation patterns in the music."""
    # Implementation would check for off-beat accents, ties across beats, etc.
    # For now, stub that checks for ties + certain rhythm patterns
    if extraction_result.has_ties:
        # More sophisticated detection could be added
        return True
    return False


@register_custom_detector("detect_any_key_signature")
def detect_any_key_signature(extraction_result, score) -> bool:
    """Detect presence of any key signature."""
    return len(extraction_result.key_signatures) > 0


@register_custom_detector("detect_ties")
def detect_ties(extraction_result, score) -> bool:
    """Detect presence of tied notes."""
    return extraction_result.has_ties


@register_custom_detector("detect_hemiola")
def detect_hemiola(extraction_result, score) -> bool:
    """Detect hemiola patterns (3 against 2)."""
    # Stub - would need to analyze rhythm groupings
    return False


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_detection_rule(capability_name: str, rule_config: Optional[Dict]) -> DetectionRule:
    """
    Validate a detection rule configuration.
    
    Returns a DetectionRule with is_valid=False and errors if invalid.
    """
    errors = []
    
    # Null/missing detection = not auto-detectable
    if rule_config is None:
        return DetectionRule(
            capability_name=capability_name,
            detection_type=None,
            config={},
            is_valid=True,
        )
    
    # Must have a type
    rule_type = rule_config.get("type")
    if not rule_type:
        errors.append("Missing 'type' field")
        return DetectionRule(
            capability_name=capability_name,
            detection_type=None,
            config=rule_config,
            is_valid=False,
            validation_errors=errors,
        )
    
    # Validate type is known
    try:
        detection_type = DetectionType(rule_type)
    except ValueError:
        errors.append(f"Unknown detection type: {rule_type}")
        return DetectionRule(
            capability_name=capability_name,
            detection_type=None,
            config=rule_config,
            is_valid=False,
            validation_errors=errors,
        )
    
    # Type-specific validation
    if detection_type == DetectionType.ELEMENT:
        if "class" not in rule_config:
            errors.append("'element' type requires 'class' field")
    
    elif detection_type == DetectionType.VALUE_MATCH:
        if "source" not in rule_config:
            errors.append("'value_match' type requires 'source' field")
        elif rule_config["source"] not in VALID_SOURCES:
            errors.append(f"Invalid source: {rule_config['source']}")
        if "field" not in rule_config:
            errors.append("'value_match' type requires 'field' field")
        if not any(k in rule_config for k in ["eq", "contains", "gte", "lte"]):
            errors.append("'value_match' type requires one of: eq, contains, gte, lte")
    
    elif detection_type == DetectionType.COMPOUND:
        if "source" not in rule_config:
            errors.append("'compound' type requires 'source' field")
        elif rule_config["source"] not in VALID_SOURCES:
            errors.append(f"Invalid source: {rule_config['source']}")
        if "conditions" not in rule_config or not isinstance(rule_config["conditions"], list):
            errors.append("'compound' type requires 'conditions' array")
    
    elif detection_type == DetectionType.INTERVAL:
        if "quality" not in rule_config:
            errors.append("'interval' type requires 'quality' field")
    
    elif detection_type == DetectionType.TEXT_MATCH:
        if "source" not in rule_config:
            errors.append("'text_match' type requires 'source' field")
        if "contains" not in rule_config and "equals" not in rule_config:
            errors.append("'text_match' type requires 'contains' or 'equals' field")
    
    elif detection_type == DetectionType.TIME_SIGNATURE:
        if "numerator" not in rule_config:
            errors.append("'time_signature' type requires 'numerator' field")
        if "denominator" not in rule_config:
            errors.append("'time_signature' type requires 'denominator' field")
    
    elif detection_type == DetectionType.RANGE:
        if "min_semitones" not in rule_config and "max_semitones" not in rule_config:
            errors.append("'range' type requires at least one of: min_semitones, max_semitones")
    
    elif detection_type == DetectionType.CUSTOM:
        if "function" not in rule_config:
            errors.append("'custom' type requires 'function' field")
        elif rule_config["function"] not in CUSTOM_DETECTORS:
            errors.append(f"Unknown custom function: {rule_config['function']}")
    
    return DetectionRule(
        capability_name=capability_name,
        detection_type=detection_type,
        config=rule_config,
        is_valid=len(errors) == 0,
        validation_errors=errors,
    )


# =============================================================================
# CAPABILITY REGISTRY CLASS
# =============================================================================

class CapabilityRegistry:
    """
    Registry for capability detection rules.
    
    Loads rules from capabilities.json, validates them at startup,
    and provides detection against MusicXML extraction results.
    """
    
    def __init__(self, capabilities_path: Optional[str] = None):
        """
        Initialize the registry.
        
        Args:
            capabilities_path: Path to capabilities.json. If None, uses default.
        """
        self.capabilities_path = capabilities_path or self._default_path()
        self.rules: Dict[str, DetectionRule] = {}
        self.capabilities_by_domain: Dict[str, List[str]] = {}
        self._loaded = False
    
    def _default_path(self) -> str:
        """Get default path to capabilities.json."""
        base = Path(__file__).parent.parent
        return str(base / "resources" / "capabilities.json")
    
    def load(self) -> Dict[str, List[str]]:
        """
        Load and validate all capability detection rules.
        
        Returns:
            Dict of validation issues: {"warnings": [...], "errors": [...]}
        """
        issues = {"warnings": [], "errors": []}
        
        try:
            with open(self.capabilities_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            issues["errors"].append(f"Failed to load capabilities.json: {e}")
            return issues
        
        capabilities = data.get("capabilities", [])
        
        for cap in capabilities:
            name = cap.get("name")
            if not name:
                issues["errors"].append(f"Capability missing 'name': {cap}")
                continue
            
            # Get detection rule (may be None/missing)
            detection_config = cap.get("music21_detection")
            
            # Validate the rule
            rule = validate_detection_rule(name, detection_config)
            self.rules[name] = rule
            
            # Track by domain
            domain = cap.get("domain", "unknown")
            if domain not in self.capabilities_by_domain:
                self.capabilities_by_domain[domain] = []
            self.capabilities_by_domain[domain].append(name)
            
            # Log validation issues
            if not rule.is_valid:
                for error in rule.validation_errors:
                    msg = f"Capability '{name}': {error}"
                    issues["warnings"].append(msg)
                    logger.warning(msg)
        
        self._loaded = True
        
        # Summary
        total = len(self.rules)
        detectable = sum(1 for r in self.rules.values() if r.detection_type is not None)
        invalid = sum(1 for r in self.rules.values() if not r.is_valid)
        
        logger.info(f"Loaded {total} capabilities: {detectable} detectable, {total - detectable} not auto-detectable, {invalid} invalid rules")
        
        return issues
    
    def get_rule(self, capability_name: str) -> Optional[DetectionRule]:
        """Get detection rule for a capability."""
        return self.rules.get(capability_name)
    
    def get_detectable_capabilities(self) -> List[str]:
        """Get list of capabilities that have valid detection rules."""
        return [
            name for name, rule in self.rules.items()
            if rule.detection_type is not None and rule.is_valid
        ]
    
    def get_capabilities_by_type(self, detection_type: DetectionType) -> List[str]:
        """Get capabilities using a specific detection type."""
        return [
            name for name, rule in self.rules.items()
            if rule.detection_type == detection_type and rule.is_valid
        ]


# =============================================================================
# DETECTION ENGINE
# =============================================================================

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
            return self._check_element(rule.config, result)
        
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
    
    def _check_element(self, config: Dict, result) -> bool:
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
        }
        if class_name in articulation_map:
            return articulation_map[class_name] in result.articulations
        
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
        if source == "tempos":
            texts = result.tempo_markings
        elif source == "expressions":
            texts = result.expression_terms
        elif source == "dynamics":
            texts = result.dynamics
        else:
            return False
        
        for text in texts:
            text_lower = text.lower()
            if equals and text_lower == equals:
                return True
            if contains and contains in text_lower:
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
        
        if source == "notes":
            # Return note value info as pseudo-objects
            items = []
            for note_type, count in result.note_values.items():
                items.append({"type": note_type.replace("note_", ""), "count": count})
            # Add dotted notes
            for dotted in result.dotted_notes:
                items.append({"type": dotted, "dots": 1 if "double" not in dotted else 2})
            return items
        
        elif source == "dynamics":
            return [{"value": d.replace("dynamic_", "")} for d in result.dynamics]
        
        elif source == "rests":
            items = []
            for rest_type, count in result.rest_values.items():
                items.append({"type": rest_type.replace("rest_", ""), "count": count})
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


# =============================================================================
# GLOBAL REGISTRY INSTANCE
# =============================================================================

_registry: Optional[CapabilityRegistry] = None


def get_registry() -> CapabilityRegistry:
    """Get or create the global capability registry."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
        issues = _registry.load()
        if issues["errors"]:
            for error in issues["errors"]:
                logger.error(error)
    return _registry


def get_detection_engine() -> DetectionEngine:
    """Get a detection engine with the global registry."""
    return DetectionEngine(get_registry())
