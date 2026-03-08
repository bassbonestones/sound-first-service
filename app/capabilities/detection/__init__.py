"""
Capability Detection Engine Package

Applies detection rules to MusicXML extraction results to identify
capabilities present in a given piece of music.
"""

from .core import DetectionEngine

__all__ = ['DetectionEngine']
