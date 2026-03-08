"""
Capability detection types and schemas.

Defines the detection type enum and rule dataclass used throughout
the capability detection system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DetectionType(str, Enum):
    """Types of capability detection rules."""
    ELEMENT = "element"
    VALUE_MATCH = "value_match"
    COMPOUND = "compound"
    INTERVAL = "interval"
    TEXT_MATCH = "text_match"
    TIME_SIGNATURE = "time_signature"
    RANGE = "range"
    CUSTOM = "custom"


@dataclass
class DetectionRule:
    """Validated detection rule for a capability."""
    capability_name: str
    detection_type: Optional[DetectionType]
    config: Dict[str, Any]
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


# Valid sources for VALUE_MATCH, COMPOUND, and TEXT_MATCH rules
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
