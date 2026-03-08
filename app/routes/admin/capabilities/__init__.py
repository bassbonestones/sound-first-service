"""Admin capabilities router package.

Combines all capability admin route modules into a single router.
"""
from fastapi import APIRouter

from .list_routes import router as list_router
from .crud_routes import router as crud_router
from .bulk_routes import router as bulk_router


router = APIRouter(tags=["admin-capabilities"])

# Include all sub-routers
router.include_router(list_router)
router.include_router(crud_router)
router.include_router(bulk_router)


# Re-export schemas for backward compatibility
from .schemas import (
    DetectionRuleConfig,
    CapabilityCreateRequest,
    CapabilityUpdateRequest,
    ReorderCapabilitiesRequest,
    RenameDomainRequest,
    DETECTION_TYPES,
    DETECTION_SOURCES,
    CUSTOM_DETECTION_FUNCTIONS,
)

__all__ = [
    "router",
    "DetectionRuleConfig",
    "CapabilityCreateRequest",
    "CapabilityUpdateRequest",
    "ReorderCapabilitiesRequest",
    "RenameDomainRequest",
    "DETECTION_TYPES",
    "DETECTION_SOURCES",
    "CUSTOM_DETECTION_FUNCTIONS",
]
