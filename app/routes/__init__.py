"""API route exports.

Exports all FastAPI routers for the application including onboarding, sessions,
history, audio, materials, capabilities, users, teaching modules, admin, imports,
and generation.
"""
from .onboarding import router as onboarding_router
from .config import router as config_router
from .sessions import router as sessions_router
from .history import router as history_router
from .audio import router as audio_router
from .materials import router as materials_router
from .capabilities import router as capabilities_router
from .users import router as users_router
from .teaching_modules import router as teaching_modules_router
from .admin import router as admin_router
from .imports import router as imports_router
from .generation import router as generation_router

__all__ = [
    "onboarding_router",
    "config_router",
    "sessions_router",
    "history_router",
    "audio_router",
    "materials_router",
    "capabilities_router",
    "users_router",
    "teaching_modules_router",
    "admin_router",
    "imports_router",
    "generation_router",
]
