"""
Soft Gate Calculator Orchestration Package

Main calculator and supporting utilities for soft gate metric calculation.
"""

from .calculator import SoftGateCalculator, calculate_soft_gates
from .score_extractor import extract_note_data

__all__ = [
    "SoftGateCalculator",
    "calculate_soft_gates",
    "extract_note_data",
]
