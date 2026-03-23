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
from typing import List, Optional

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
    "sort_capabilities_by_bit_index",
    "sort_capabilities_by_bit_index_with_session",
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


def sort_capabilities_by_bit_index(capability_names: List[str]) -> List[str]:
    """
    Sort capability names by their bit_index order from the DATABASE.
    
    Queries the database for bit_index values (the source of truth).
    Capabilities without a bit_index are placed at the end.
    
    Args:
        capability_names: List of capability name strings
        
    Returns:
        List sorted by bit_index (ascending)
    """
    if not capability_names:
        return []
    
    # Import here to avoid circular imports
    from app.db import SessionLocal
    from app.models.capability_schema import Capability
    
    db = SessionLocal()
    try:
        # Query bit_index for all requested capabilities
        caps = db.query(Capability.name, Capability.bit_index).filter(
            Capability.name.in_(capability_names)
        ).all()
        
        bit_index_map = {name: (bit_idx if bit_idx is not None else 99999) for name, bit_idx in caps}
        
        return sorted(
            capability_names,
            key=lambda name: bit_index_map.get(name, 99999)
        )
    finally:
        db.close()


def sort_capabilities_by_bit_index_with_session(
    capability_names: List[str], 
    db
) -> List[str]:
    """
    Sort capability names by bit_index using an existing db session.
    
    Use this when you already have a database session (e.g., in a route handler).
    
    Args:
        capability_names: List of capability name strings
        db: SQLAlchemy Session
        
    Returns:
        List sorted by bit_index (ascending)
    """
    if not capability_names:
        return []
    
    from app.models.capability_schema import Capability
    
    caps = db.query(Capability.name, Capability.bit_index).filter(
        Capability.name.in_(capability_names)
    ).all()
    
    bit_index_map = {name: (bit_idx if bit_idx is not None else 99999) for name, bit_idx in caps}
    
    return sorted(
        capability_names,
        key=lambda name: bit_index_map.get(name, 99999)
    )
