"""
Centralized application settings using Pydantic BaseSettings.

All configuration is defined in one place with type validation,
environment variable support, and auto-documentation.

Usage:
    from app.settings import settings
    
    db_url = settings.database_url
    pool_size = settings.db_pool_size
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults and can be overridden via
    environment variables or a .env file.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ==========================================================================
    # Database Settings
    # ==========================================================================
    database_url: str = "postgresql://user:password@localhost/soundfirst"
    alembic_database_url: Optional[str] = None
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800  # Recycle connections after 30 minutes
    
    # ==========================================================================
    # Audio Rendering Settings
    # ==========================================================================
    use_direct_fluidsynth: bool = True
    """Use subprocess FluidSynth (works behind corporate firewalls)."""
    
    use_musescore: bool = False
    """Use MuseScore 4 for rendering (professional quality with Muse Sounds)."""
    
    musescore_path: str = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
    """Path to MuseScore executable."""
    
    soundfont_path: Optional[str] = None
    """Path to .sf2 soundfont file. Auto-detected if not set."""
    
    # ==========================================================================
    # API Settings
    # ==========================================================================
    api_title: str = "Sound First Service API"
    api_version: str = "1.0.0"
    api_description: str = "Backend API for Sound First music education platform"
    
    debug: bool = False
    """Enable debug mode with verbose logging."""
    
    cors_origins: str = "*"
    """Comma-separated list of allowed CORS origins."""
    
    # ==========================================================================
    # Logging Settings
    # ==========================================================================
    log_level: str = "INFO"
    """Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL."""
    
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    """Logging format string."""
    
    # ==========================================================================
    # Feature Flags
    # ==========================================================================
    enable_audio_generation: bool = True
    """Enable audio generation endpoints."""
    
    enable_admin_routes: bool = True
    """Enable admin management endpoints."""

    # ==========================================================================
    # Storage Settings
    # ==========================================================================
    storage_provider: str = "local"
    """Storage provider: 'local' or 's3'."""

    local_storage_path: str = "./uploads"
    """Local storage directory for uploaded files."""

    s3_bucket: str = ""
    """S3 bucket name for file storage."""

    s3_region: str = "us-east-1"
    """AWS S3 region."""

    s3_access_key: str = ""
    """AWS access key ID."""

    s3_secret_key: str = ""
    """AWS secret access key."""

    signed_url_expiry: int = 3600
    """Signed URL expiry time in seconds (default: 1 hour)."""

    # ==========================================================================
    # OMR Settings
    # ==========================================================================
    omr_provider: str = "mock"
    """OMR provider: 'mock', 'audiveris', 'oemer', or 'commercial'."""

    omr_api_url: str = ""
    """External OMR API URL (for commercial providers)."""

    omr_api_key: str = ""
    """External OMR API key."""

    audiveris_path: str = ""
    """Path to Audiveris executable or JAR (auto-detect if empty)."""

    audiveris_java_opts: str = "-Xmx2g"
    """JVM options for Audiveris (memory, etc.)."""

    # ==========================================================================
    # Celery / Redis Settings
    # ==========================================================================
    redis_url: str = "redis://localhost:6379/0"
    """Redis URL for Celery broker and result backend."""

    celery_broker_url: str = ""
    """Celery broker URL (defaults to redis_url if empty)."""

    celery_result_backend: str = ""
    """Celery result backend URL (defaults to redis_url if empty)."""

    celery_task_time_limit: int = 600
    """Maximum time (seconds) for a single task."""

    celery_task_soft_time_limit: int = 540
    """Soft time limit for tasks (allows graceful shutdown)."""

    @property
    def effective_celery_broker(self) -> str:
        """Return the Celery broker URL to use."""
        return self.celery_broker_url or self.redis_url

    @property
    def effective_celery_backend(self) -> str:
        """Return the Celery result backend URL to use."""
        return self.celery_result_backend or self.redis_url

    @property
    def effective_database_url(self) -> str:
        """Return the database URL to use (prefers ALEMBIC_DATABASE_URL)."""
        return self.alembic_database_url or self.database_url
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Uses lru_cache for performance - settings are loaded once
    and reused throughout the application lifecycle.
    """
    return Settings()


# Convenience singleton for direct import
settings = get_settings()
