"""
Practice Engine Database Service

This module provides database integration for the practice engine.

REFACTORED: Implementation moved to app/services/engine/ package.
This file is a thin re-export for backward compatibility.
"""

# Re-export the service class from the new location
from .services.engine import PracticeEngineService

__all__ = ['PracticeEngineService']
