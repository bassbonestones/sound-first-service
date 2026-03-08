"""
Capability Registry for Sound First - Backwards Compatibility Module

This module re-exports the capability detection system from app.capabilities.
For new code, prefer importing directly from app.capabilities.

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

# Re-export everything from the new capabilities module for backwards compatibility
from app.capabilities import (
    # Types
    DetectionType,
    DetectionRule,
    VALID_SOURCES,
    # Classes
    CapabilityRegistry,
    DetectionEngine,
    # Functions
    get_registry,
    get_detection_engine,
    validate_detection_rule,
    register_custom_detector,
    # Registry
    CUSTOM_DETECTORS,
)

__all__ = [
    "DetectionType",
    "DetectionRule",
    "VALID_SOURCES",
    "CapabilityRegistry",
    "DetectionEngine",
    "get_registry",
    "get_detection_engine",
    "validate_detection_rule",
    "register_custom_detector",
    "CUSTOM_DETECTORS",
]
