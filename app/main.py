from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    onboarding_router,
    config_router,
    sessions_router,
    history_router,
    audio_router,
    materials_router,
    capabilities_router,
    users_router,
    admin_router,
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(onboarding_router)
app.include_router(config_router)
app.include_router(sessions_router)
app.include_router(history_router)
app.include_router(audio_router)
app.include_router(materials_router)
app.include_router(capabilities_router)
app.include_router(users_router)
app.include_router(admin_router)

