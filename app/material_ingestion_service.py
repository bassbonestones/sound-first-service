"""
Material Ingestion Service - backwards-compatible facade.

This module re-exports from app.services.material_ingestion_service
for backwards compatibility.
"""

from app.services.material_ingestion_service import (
    MaterialEntry,
    IngestionResult,
    MaterialIngestionService,
    ingest_materials,
    export_materials_json,
)

__all__ = [
    "MaterialEntry",
    "IngestionResult",
    "MaterialIngestionService",
    "ingest_materials",
    "export_materials_json",
]
