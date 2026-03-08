"""
Material management service.

REFACTORED: This module now re-exports from the material package.
See app/services/material/ for implementation.
"""

from .material import (
    MaterialService,
    get_material_service,
    UploadResult,
    ReanalyzeResult,
    BatchReanalyzeResult,
)

__all__ = [
    "MaterialService",
    "get_material_service",
    "UploadResult",
    "ReanalyzeResult",
    "BatchReanalyzeResult",
]
