"""Admin route package - combines all admin sub-routers."""
from fastapi import APIRouter

from .capabilities import router as capabilities_router
from .materials import router as materials_router
from .users import router as users_router
from .focus_cards import router as focus_cards_router
from .soft_gates import router as soft_gates_router
from .engine import router as engine_router

# Main admin router that combines all sub-routers
router = APIRouter(prefix="/admin", tags=["admin"])

# Include all sub-routers
router.include_router(capabilities_router)
router.include_router(materials_router)
router.include_router(users_router)
router.include_router(focus_cards_router)
router.include_router(soft_gates_router)
router.include_router(engine_router)

__all__ = ["router"]
