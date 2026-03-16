"""Data models for material ingestion."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class MaterialEntry:
    """Represents a material entry in materials.json."""
    title: str
    musicxml_file: str
    original_key_center: Optional[str] = None
    allowed_keys: str = ""
    required_capability_ids: str = ""
    scaffolding_capability_ids: str = ""
    pitch_reference_type: str = "TONAL"
    pitch_ref_json: str = "{}"
    spelling_policy: str = "from_key"
    
    # Analysis results (generated)
    detected_capabilities: Optional[List[str]] = None
    soft_gates: Optional[Dict[str, Any]] = None
    range_analysis: Optional[Dict[str, Any]] = None


@dataclass
class IngestionResult:
    """Result of an ingestion run."""
    files_scanned: int
    files_analyzed: int
    files_skipped: int
    orphans_removed: int
    errors: List[str]
    analyzed_materials: List[str]
