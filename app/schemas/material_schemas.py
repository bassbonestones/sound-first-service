"""Material-related Pydantic models."""
from pydantic import BaseModel
from typing import List, Optional


class MaterialUpload(BaseModel):
    """Input model for material upload."""
    title: str
    musicxml_content: str
    original_key_center: Optional[str] = None
    allowed_keys: Optional[List[str]] = None  # If not provided, will default to common keys


class MaterialAnalysisResponse(BaseModel):
    """Response model for material analysis."""
    material_id: int
    title: str
    extracted_capabilities: List[str]
    range_analysis: Optional[dict]
    chromatic_complexity: float
    measure_count: int
    warnings: List[str] = []


class BatchIngestionRequest(BaseModel):
    """Request model for batch material ingestion."""
    analyze_missing_only: bool = True
    overwrite: bool = False
    specific_files: Optional[List[str]] = None
    specific_metrics: Optional[List[str]] = None  # ["capabilities", "soft_gates"]


class BatchIngestionResponse(BaseModel):
    """Response model for batch ingestion."""
    files_scanned: int
    files_analyzed: int
    files_skipped: int
    orphans_removed: int
    errors: List[str]
    analyzed_materials: List[str]


class ReanalyzeRequest(BaseModel):
    """Request model for selective re-analysis."""
    metrics: Optional[List[str]] = None  # ["capabilities", "soft_gates", "range"]
    # If None, re-analyzes everything


class ReanalyzeResponse(BaseModel):
    """Response model for re-analysis."""
    material_id: int
    title: str
    metrics_updated: List[str]
    capabilities_count: Optional[int] = None
    soft_gates: Optional[dict] = None
    range_analysis: Optional[dict] = None


class BatchReanalyzeRequest(BaseModel):
    """Request model for batch re-analysis."""
    metrics: Optional[List[str]] = None
    material_ids: Optional[List[int]] = None  # If None, re-analyzes all


class BatchReanalyzeResponse(BaseModel):
    """Response model for batch re-analysis."""
    total_materials: int
    materials_updated: int
    materials_failed: int
    errors: List[str]
