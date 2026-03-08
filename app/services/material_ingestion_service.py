"""
Material Ingestion Service - backwards-compatible facade.

This module re-exports from app.services.ingestion package
for backwards compatibility.
"""

from .ingestion import (
    MaterialEntry,
    IngestionResult,
    MaterialIngestionService,
    ingest_materials,
    export_materials_json,
    analyze_material,
    detect_all_capabilities,
    format_soft_gates,
)

__all__ = [
    "MaterialEntry",
    "IngestionResult",
    "MaterialIngestionService",
    "ingest_materials",
    "export_materials_json",
    "analyze_material",
    "detect_all_capabilities",
    "format_soft_gates",
]
