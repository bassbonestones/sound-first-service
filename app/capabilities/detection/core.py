"""
Detection Engine Core

Main DetectionEngine class that applies detection rules to extraction results.
"""

import logging
from typing import Any, Dict, Set

from app.capabilities.types import DetectionRule, DetectionType
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.custom_detectors import CUSTOM_DETECTORS

from .element_matchers import check_element
from .source_extractors import get_source_data
from .value_matchers import check_value_condition

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
        extraction_result: Any,  # ExtractionResult from musicxml_analyzer
        score: Any = None,  # Optional music21 score for custom detectors
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
        result: Any,  # ExtractionResult
        score: Any,
    ) -> bool:
        """Check if a single detection rule matches."""
        
        if rule.detection_type == DetectionType.ELEMENT:
            return check_element(rule.config, result, score)
        
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
    
    def _check_value_match(self, config: Dict[str, Any], result: Any) -> bool:
        """Check for field value match on source objects."""
        source = config.get("source", "")
        field_path = config.get("field", "")
        
        source_data = get_source_data(source, result)
        if not source_data:
            return False
        
        for item in source_data:
            if check_value_condition(item, field_path, config):
                return True
        
        return False
    
    def _check_compound(self, config: Dict[str, Any], result: Any) -> bool:
        """Check multiple conditions (AND logic)."""
        source = config.get("source", "")
        conditions = config.get("conditions", [])
        
        source_data = get_source_data(source, result)
        if not source_data:
            return False
        
        # An item must satisfy ALL conditions
        for item in source_data:
            all_match = True
            for cond in conditions:
                field_path = cond.get("field", "")
                if not check_value_condition(item, field_path, cond):
                    all_match = False
                    break
            if all_match:
                return True
        
        return False
    
    def _check_interval(self, config: Dict[str, Any], result: Any) -> bool:
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
    
    def _check_text_match(self, config: Dict[str, Any], result: Any) -> bool:
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
    
    def _check_time_signature(self, config: Dict[str, Any], result: Any) -> bool:
        """Check for time signature match."""
        numerator = config.get("numerator")
        denominator = config.get("denominator")
        
        expected = f"time_sig_{numerator}_{denominator}"
        return expected in result.time_signatures
    
    def _check_range(self, config: Dict[str, Any], result: Any) -> bool:
        """Check for interval size range."""
        min_semi = config.get("min_semitones", 0)
        max_semi = config.get("max_semitones", 999)
        
        if not result.range_analysis:
            return False
        
        range_semi = result.range_analysis.range_semitones
        return bool(min_semi <= range_semi <= max_semi)
    
    def _check_custom(self, config: Dict[str, Any], result: Any, score: Any) -> bool:
        """Execute custom detection function."""
        func_name = config.get("function")
        if func_name not in CUSTOM_DETECTORS:
            return False
        
        return bool(CUSTOM_DETECTORS[func_name](result, score))
