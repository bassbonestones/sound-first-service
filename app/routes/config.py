"""Configuration, health, and logging endpoints."""
from fastapi import APIRouter, Body
import datetime
import json
import logging

from app.db import check_db_health
from app.schemas import ClientLogIn, ConfigUpdateIn
from app.schemas.user_schemas import (
    HealthCheckOut, LoggedOut, SessionConfigOut, ConfigUpdateOut
)
from app.session_config import (
    CAPABILITY_WEIGHTS,
    DIFFICULTY_WEIGHTS,
    NOVELTY_REINFORCEMENT,
    AVG_MINI_SESSION_MINUTES,
    WRAP_UP_THRESHOLD_MINUTES,
    KEYS_PER_INTENSITY,
)

router = APIRouter(tags=["config"])


@router.get(
    "/health",
    response_model=HealthCheckOut,
    description="Health check with database connection pool status",
)
def health_check() -> HealthCheckOut:
    """
    Health check endpoint with database connection pool status.
    
    Returns overall health status and database pool metrics:
    - pool_size: Base number of connections maintained
    - checked_in: Available connections in pool
    - checked_out: Connections currently in use
    - overflow: Additional connections beyond pool_size
    """
    db_status = check_db_health()
    overall_status = "healthy" if db_status["status"] == "healthy" else "unhealthy"
    return {  # type: ignore[return-value]
        "status": overall_status,
        "database": {
            "pool_size": db_status["pool_size"],
            "checked_in": db_status["checked_in"],
            "checked_out": db_status["checked_out"],
            "overflow": db_status["overflow"],
            "error": db_status.get("error"),
        },
    }


@router.post(
    "/log/client",
    response_model=LoggedOut,
    description="Receive and log client app events for server-side tracking",
)
def log_client_event(log: ClientLogIn = Body(...)) -> LoggedOut:
    """
    Receive log events from client apps (web/mobile) for server-side logging.
    Useful for tracking startup timing, errors, and performance metrics.
    """
    logger = logging.getLogger("client")
    
    ts = log.timestamp or datetime.datetime.now().isoformat()
    logger.info(f"[CLIENT] {log.event} | {ts} | {json.dumps(log.data)}")
    
    return {"status": "logged"}  # type: ignore[return-value]


@router.get(
    "/config",
    response_model=SessionConfigOut,
    description="Get current session generation configuration",
)
def get_session_config() -> SessionConfigOut:
    """Get current session generation configuration."""
    return {  # type: ignore[return-value]
        "capability_weights": CAPABILITY_WEIGHTS,
        "difficulty_weights": DIFFICULTY_WEIGHTS,
        "novelty_reinforcement": NOVELTY_REINFORCEMENT,
        "avg_mini_session_minutes": AVG_MINI_SESSION_MINUTES,
        "wrap_up_threshold_minutes": WRAP_UP_THRESHOLD_MINUTES,
        "keys_per_intensity": KEYS_PER_INTENSITY,
    }


@router.patch(
    "/config",
    response_model=ConfigUpdateOut,
    description="Update session configuration at runtime (non-persistent)",
)
def update_session_config(data: ConfigUpdateIn = Body(...)) -> ConfigUpdateOut:
    """
    Update session generation configuration at runtime.
    Changes are applied immediately but not persisted across restarts.
    """
    import app.session_config as config
    
    updated = []
    
    if data.capability_weights:
        config.CAPABILITY_WEIGHTS.update(data.capability_weights)
        updated.append("capability_weights")
    
    if data.difficulty_weights:
        config.DIFFICULTY_WEIGHTS.update(data.difficulty_weights)
        updated.append("difficulty_weights")
    
    if data.novelty_reinforcement:
        config.NOVELTY_REINFORCEMENT.update(data.novelty_reinforcement)
        updated.append("novelty_reinforcement")
    
    return {"status": "success", "updated": updated}  # type: ignore[return-value]
