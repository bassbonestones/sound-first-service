"""
Detectors Package

Aggregates all custom detection functions from domain-specific modules.
Each module registers its detectors into its own CUSTOM_DETECTORS dict.
This __init__ merges them all into a single registry.
"""

from typing import Callable, Dict

# Import all detector modules to trigger registration
from .rhythm_detectors import CUSTOM_DETECTORS as rhythm_detectors
from .accidental_detectors import CUSTOM_DETECTORS as accidental_detectors
from .dynamics_detectors import CUSTOM_DETECTORS as dynamics_detectors
from .structure_detectors import CUSTOM_DETECTORS as structure_detectors
from .notation_detectors import CUSTOM_DETECTORS as notation_detectors
from .pattern_detectors import CUSTOM_DETECTORS as pattern_detectors

# Merge all detectors into a single registry
CUSTOM_DETECTORS: Dict[str, Callable[..., bool]] = {}
CUSTOM_DETECTORS.update(rhythm_detectors)
CUSTOM_DETECTORS.update(accidental_detectors)
CUSTOM_DETECTORS.update(dynamics_detectors)
CUSTOM_DETECTORS.update(structure_detectors)
CUSTOM_DETECTORS.update(notation_detectors)
CUSTOM_DETECTORS.update(pattern_detectors)

# Register helper for external modules
def register_custom_detector(name: str) -> Callable[[Callable[..., bool]], Callable[..., bool]]:
    """Decorator to register a custom detection function."""
    def decorator(func: Callable[..., bool]) -> Callable[..., bool]:
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator

__all__ = ['CUSTOM_DETECTORS', 'register_custom_detector']
