"""
Custom detection functions for capability detection.

These functions are registered with the @register_custom_detector decorator
and can be referenced in capabilities.json via the "custom" detection type.

NOTE: This file re-exports from the detectors/ package for backward compatibility.
All detector implementations now live in domain-specific modules under detectors/.
"""

# Re-export everything from the detectors package
from .detectors import CUSTOM_DETECTORS, register_custom_detector

__all__ = ['CUSTOM_DETECTORS', 'register_custom_detector']
