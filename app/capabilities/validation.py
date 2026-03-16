"""
Validation functions for capability detection rules.

Validates detection rules from capabilities.json at startup.
"""

from typing import Any, Dict, Optional

from .types import DetectionRule, DetectionType, VALID_SOURCES
from .custom_detectors import CUSTOM_DETECTORS


def validate_detection_rule(capability_name: str, rule_config: Optional[Dict[str, Any]]) -> DetectionRule:
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
