"""
Capability detection module for Sound First.

This module provides:
- CapabilityRegistry: Loads and validates detection rules from capabilities.json
- DetectionEngine: Applies rules to detect capabilities in MusicXML
- Detection types and rule definitions

Usage:
    from app.capabilities import get_registry, get_detection_engine
    
    # Get the global registry (loads rules on first access)
    registry = get_registry()
    
    # Get a detection engine
    engine = get_detection_engine()
    detected = engine.detect_capabilities(extraction_result, score)
"""

import logging
from typing import Optional

from .types import DetectionType, DetectionRule, VALID_SOURCES
from .registry import CapabilityRegistry
from .engine import DetectionEngine
from .custom_detectors import CUSTOM_DETECTORS, register_custom_detector
from .validation import validate_detection_rule

logger = logging.getLogger(__name__)

__all__ = [
    # Types
    "DetectionType",
    "DetectionRule",
    "VALID_SOURCES",
    # Classes
    "CapabilityRegistry",
    "DetectionEngine",
    # Functions
    "get_registry",
    "get_detection_engine",
    "validate_detection_rule",
    "register_custom_detector",
    # Registry
    "CUSTOM_DETECTORS",
]


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
