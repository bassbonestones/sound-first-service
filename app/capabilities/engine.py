"""
Detection Engine for capability detection.

REFACTORED: Implementation moved to app/capabilities/detection/ package.
This file is a thin re-export for backward compatibility.
"""

from .detection import DetectionEngine

__all__ = ['DetectionEngine']
