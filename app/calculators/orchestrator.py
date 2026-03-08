"""
Soft Gate Calculator Orchestrator

REFACTORED: This module now re-exports from the orchestration package.
See app/calculators/orchestration/ for implementation.
"""

from .orchestration import SoftGateCalculator, calculate_soft_gates, extract_note_data

__all__ = ["SoftGateCalculator", "calculate_soft_gates", "extract_note_data"]
