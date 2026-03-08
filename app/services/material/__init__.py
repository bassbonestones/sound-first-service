"""
Material Service Package

Handles business logic for material upload, analysis, and reanalysis operations.
"""

from .service import MaterialService, get_material_service
from .models import UploadResult, ReanalyzeResult, BatchReanalyzeResult

__all__ = [
    "MaterialService",
    "get_material_service",
    "UploadResult",
    "ReanalyzeResult",
    "BatchReanalyzeResult",
]
