"""
Material Ingestion Package

Provides batch MusicXML analysis and materials.json management.

Classes:
    MaterialIngestionService: Main service for batch analysis
    
Functions:
    ingest_materials: Convenience function for batch ingestion
    export_materials_json: Export with archive backup
    analyze_material: Analyze a single MusicXML file
    detect_all_capabilities: Detect capabilities from content
    format_soft_gates: Format soft gates dict for JSON

Models:
    MaterialEntry: TypedDict for material metadata
    IngestionResult: Dataclass for batch results
"""

from .models import MaterialEntry, IngestionResult
from .analyzer import (
    analyze_material,
    detect_all_capabilities,
    format_soft_gates,
)
from .service import (
    MaterialIngestionService,
    ingest_materials,
    export_materials_json,
)

__all__ = [
    # Service
    "MaterialIngestionService",
    # Convenience functions
    "ingest_materials",
    "export_materials_json",
    # Analyzer functions
    "analyze_material",
    "detect_all_capabilities",
    "format_soft_gates",
    # Models
    "MaterialEntry",
    "IngestionResult",
]
