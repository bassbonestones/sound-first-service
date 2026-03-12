"""FastAPI application entry point.

Configures the main FastAPI app with routes, middleware, exception handlers,
and application metadata.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.routes import (
    onboarding_router,
    config_router,
    sessions_router,
    history_router,
    audio_router,
    materials_router,
    capabilities_router,
    users_router,
    teaching_modules_router,
    admin_router,
)
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# API tags metadata for OpenAPI documentation
tags_metadata = [
    {
        "name": "config",
        "description": "Health checks, client logging, and session configuration.",
    },
    {
        "name": "onboarding",
        "description": "User registration, Day 0 setup, and initial calibration.",
    },
    {
        "name": "users",
        "description": "User profile management and instrument configuration.",
    },
    {
        "name": "sessions",
        "description": "Practice session creation, mini-sessions, and attempt recording.",
    },
    {
        "name": "materials",
        "description": "Music materials and MusicXML content retrieval.",
    },
    {
        "name": "capabilities",
        "description": "User capability tracking and progression.",
    },
    {
        "name": "history",
        "description": "Practice history, analytics, and spaced repetition data.",
    },
    {
        "name": "audio",
        "description": "Audio file generation including metronome and pitch drones.",
    },
    {
        "name": "teaching-modules",
        "description": "Teaching modules and lesson content for capabilities.",
    },
    {
        "name": "admin",
        "description": "Administrative endpoints for user management and diagnostics.",
    },
    {
        "name": "admin-users",
        "description": "Admin: User progression, capabilities, and soft gates management.",
    },
    {
        "name": "admin-materials",
        "description": "Admin: Material analysis and gate checking.",
    },
    {
        "name": "admin-focus-cards",
        "description": "Admin: Focus card CRUD operations.",
    },
    {
        "name": "admin-soft-gates",
        "description": "Admin: Soft gate rules and user state management.",
    },
    {
        "name": "admin-capabilities",
        "description": "Admin: Capability CRUD, reordering, and export.",
    },
    {
        "name": "admin-engine",
        "description": "Admin: Session engine configuration and tuning.",
    },
]

app = FastAPI(
    title="Sound First API",
    description="""
## Sound First Music Education API

Backend service for the Sound First music education app, providing:

- **Capability-based learning**: Track and develop musical skills
- **Adaptive practice sessions**: Personalized material selection
- **Spaced repetition**: Optimized review scheduling
- **Teaching modules**: Structured lessons with exercises

### Authentication

Currently using user_id query parameters. OAuth2 integration planned.

### Error Responses

All errors return a consistent JSON structure:
```json
{
    "error": true,
    "status_code": <int>,
    "detail": "<message>",
    "path": "<request_path>"
}
```
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Sound First Support",
        "email": "support@soundfirst.app",
    },
    license_info={
        "name": "Proprietary",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with detailed field information."""
    errors = exc.errors()
    logger.warning(
        f"Validation error at {request.method} {request.url.path}: {errors}"
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "status_code": 422,
            "detail": "Validation error",
            "errors": [
                {
                    "field": ".".join(str(loc) for loc in err.get("loc", [])),
                    "message": err.get("msg", "Invalid value"),
                    "type": err.get("type", "value_error"),
                }
                for err in errors
            ],
            "path": str(request.url.path),
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity constraint violations."""
    logger.warning(
        f"Database integrity error at {request.method} {request.url.path}: {str(exc.orig)}"
    )
    return JSONResponse(
        status_code=409,
        content={
            "error": True,
            "status_code": 409,
            "detail": "Database constraint violation",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database connection and query errors."""
    logger.error(
        f"Database error at {request.method} {request.url.path}:\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": True,
            "status_code": 503,
            "detail": "Database service unavailable",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent JSON response."""
    logger.warning(
        f"HTTP {exc.status_code} at {request.method} {request.url.path}: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError with 400 Bad Request."""
    logger.warning(f"ValueError at {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": True,
            "status_code": 400,
            "detail": f"Invalid value: {str(exc)}",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions."""
    # Log the full traceback for debugging
    logger.error(
        f"Unhandled exception at {request.method} {request.url.path}:\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detail": "Internal server error",
            "path": str(request.url.path),
        },
    )


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
app.include_router(teaching_modules_router)
app.include_router(admin_router)

