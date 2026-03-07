"""Configuration, health, and logging endpoints."""
from fastapi import APIRouter, Body
import datetime
import json
import logging

from app.schemas import ClientLogIn, ConfigUpdateIn
from app.session_config import (
    CAPABILITY_WEIGHTS,
    DIFFICULTY_WEIGHTS,
    NOVELTY_REINFORCEMENT,
    AVG_MINI_SESSION_MINUTES,
    WRAP_UP_THRESHOLD_MINUTES,
    KEYS_PER_INTENSITY,
)

router = APIRouter(tags=["config"])


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.post("/log/client")
def log_client_event(log: ClientLogIn = Body(...)):
    """
    Receive log events from client apps (web/mobile) for server-side logging.
    Useful for tracking startup timing, errors, and performance metrics.
    """
    logger = logging.getLogger("client")
    
    ts = log.timestamp or datetime.datetime.now().isoformat()
    logger.info(f"[CLIENT] {log.event} | {ts} | {json.dumps(log.data)}")
    
    # Also print to stdout for uvicorn visibility
    print(f"[CLIENT LOG] {log.event} | {ts} | {json.dumps(log.data)}")
    
    return {"status": "logged"}


@router.get("/config")
def get_session_config():
    """Get current session generation configuration."""
    return {
        "capability_weights": CAPABILITY_WEIGHTS,
        "difficulty_weights": DIFFICULTY_WEIGHTS,
        "novelty_reinforcement": NOVELTY_REINFORCEMENT,
        "avg_mini_session_minutes": AVG_MINI_SESSION_MINUTES,
        "wrap_up_threshold_minutes": WRAP_UP_THRESHOLD_MINUTES,
        "keys_per_intensity": KEYS_PER_INTENSITY,
    }


@router.patch("/config")
def update_session_config(data: ConfigUpdateIn = Body(...)):
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
    
    return {"status": "success", "updated": updated}
