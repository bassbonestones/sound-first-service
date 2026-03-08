"""
Material Service Result Models

Dataclasses for material service operation results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class UploadResult:
    """Result from uploading a new material."""
    material_id: int
    title: str
    extracted_capabilities: List[str]
    range_analysis: Optional[Dict] = None
    chromatic_complexity: Optional[float] = None
    measure_count: Optional[int] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class ReanalyzeResult:
    """Result from reanalyzing a material."""
    material_id: int
    title: str
    metrics_updated: List[str]
    capabilities_count: Optional[int] = None
    soft_gates: Optional[Dict] = None
    range_analysis: Optional[Dict] = None
    unified_scores: Optional[Dict] = None
    unified_scores_error: Optional[str] = None
    difficulty_scores: Optional[Dict] = None


@dataclass
class BatchReanalyzeResult:
    """Result from batch reanalysis."""
    total_materials: int
    materials_updated: int
    materials_failed: int
    errors: List[str] = field(default_factory=list)
