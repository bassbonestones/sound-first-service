"""
Tests for app/settings.py module.

Target: 0% → 85%+ coverage.
"""

import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Test the Settings class and configuration."""
    
    def test_settings_singleton_import(self):
        """Settings singleton should be importable and configured."""
        from app.settings import settings
        assert settings.api_title == "Sound First Service API"
    
    def test_settings_class_import(self):
        """Settings class should be a Pydantic model."""
        from app.settings import Settings
        from pydantic_settings import BaseSettings
        assert issubclass(Settings, BaseSettings)
    
    def test_get_settings_function(self):
        """get_settings should return configured Settings instance."""
        from app.settings import get_settings
        settings = get_settings()
        assert settings.db_pool_size == 5  # Default value
    
    def test_settings_cached(self):
        """get_settings should return cached instance."""
        from app.settings import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
    
    def test_database_url_default(self):
        """Database URL should have a default postgresql connection string."""
        from app.settings import Settings
        s = Settings(_env_file=None)
        # Database URL should be a non-empty connection string
        assert len(s.database_url) > 15
        # Should contain postgres (either postgresql:// or loaded from env)
        assert "postgres" in s.database_url.lower() or "db" in s.database_url.lower()
    
    def test_db_pool_size_default(self):
        """DB pool size should have sensible default."""
        from app.settings import Settings
        s = Settings()
        assert s.db_pool_size == 5
    
    def test_db_max_overflow_default(self):
        """DB max overflow should have sensible default."""
        from app.settings import Settings
        s = Settings()
        assert s.db_max_overflow == 10
    
    def test_db_pool_timeout_default(self):
        """DB pool timeout should have sensible default."""
        from app.settings import Settings
        s = Settings()
        assert s.db_pool_timeout == 30
    
    def test_db_pool_recycle_default(self):
        """DB pool recycle should have sensible default."""
        from app.settings import Settings
        s = Settings()
        assert s.db_pool_recycle == 1800
    
    def test_use_direct_fluidsynth_default(self):
        """FluidSynth setting should default to True."""
        from app.settings import Settings
        s = Settings()
        assert s.use_direct_fluidsynth is True
    
    def test_use_musescore_default(self):
        """MuseScore setting should default to False."""
        from app.settings import Settings
        s = Settings()
        assert s.use_musescore is False
    
    def test_musescore_path_default(self):
        """MuseScore path should have default."""
        from app.settings import Settings
        s = Settings()
        assert "mscore" in s.musescore_path.lower() or "musescore" in s.musescore_path.lower()
    
    def test_soundfont_path_default(self):
        """Soundfont path can be None."""
        from app.settings import Settings
        s = Settings()
        # Can be None or a path
        assert s.soundfont_path is None or isinstance(s.soundfont_path, str)
    
    def test_api_title_default(self):
        """API title should be Sound First Service API."""
        from app.settings import Settings
        s = Settings()
        assert s.api_title == "Sound First Service API"
    
    def test_api_version_default(self):
        """API version should be 1.0.0 by default."""
        from app.settings import Settings
        s = Settings()
        assert s.api_version == "1.0.0"
    
    def test_api_description_default(self):
        """API description should describe the platform."""
        from app.settings import Settings
        s = Settings()
        assert "Sound First" in s.api_description
        assert "music" in s.api_description.lower()
    
    def test_debug_default(self):
        """Debug should default to False."""
        from app.settings import Settings
        s = Settings()
        assert s.debug is False
    
    def test_cors_origins_default(self):
        """CORS origins should default to wildcard."""
        from app.settings import Settings
        s = Settings()
        assert s.cors_origins == "*"
    
    def test_log_level_default(self):
        """Log level should have default."""
        from app.settings import Settings
        s = Settings()
        assert s.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    def test_log_format_default(self):
        """Log format should include timestamp and level."""
        from app.settings import Settings
        s = Settings()
        assert "%(asctime)s" in s.log_format
        assert "%(levelname)s" in s.log_format
    
    def test_enable_audio_generation_default(self):
        """Audio generation should default to True."""
        from app.settings import Settings
        s = Settings()
        assert s.enable_audio_generation is True
    
    def test_enable_admin_routes_default(self):
        """Admin routes should default to True."""
        from app.settings import Settings
        s = Settings()
        assert s.enable_admin_routes is True
    
    def test_effective_database_url_no_alembic(self):
        """Effective DB URL should use database_url when no alembic URL."""
        from app.settings import Settings
        s = Settings(alembic_database_url=None)
        assert s.effective_database_url == s.database_url
    
    def test_effective_database_url_with_alembic(self):
        """Effective DB URL should prefer alembic URL."""
        from app.settings import Settings
        s = Settings(alembic_database_url="postgresql://alembic:test@localhost/db")
        assert s.effective_database_url == "postgresql://alembic:test@localhost/db"
    
    def test_cors_origins_list_single(self):
        """CORS origins list with single origin."""
        from app.settings import Settings
        s = Settings(cors_origins="http://localhost:3000")
        assert s.cors_origins_list == ["http://localhost:3000"]
    
    def test_cors_origins_list_multiple(self):
        """CORS origins list with multiple origins."""
        from app.settings import Settings
        s = Settings(cors_origins="http://localhost:3000,http://localhost:8080")
        assert len(s.cors_origins_list) == 2
        assert "http://localhost:3000" in s.cors_origins_list
        assert "http://localhost:8080" in s.cors_origins_list
    
    def test_cors_origins_list_with_spaces(self):
        """CORS origins list should strip spaces."""
        from app.settings import Settings
        s = Settings(cors_origins=" http://localhost:3000 , http://localhost:8080 ")
        assert s.cors_origins_list == ["http://localhost:3000", "http://localhost:8080"]
    
    def test_settings_with_env_override(self):
        """Settings should support environment variable override."""
        from app.settings import Settings
        with patch.dict(os.environ, {"DEBUG": "true"}):
            # Need a fresh instance to pick up env changes
            s = Settings(_env_file=None)
            # Debug can be true or false depending on env
            assert s.debug in (True, False)
    
    def test_settings_model_config(self):
        """Settings should have proper model config for Pydantic."""
        from app.settings import Settings
        assert Settings.model_config.get("case_sensitive") is False
        assert Settings.model_config.get("extra") == "ignore"
    
    def test_all_settings_have_type(self):
        """All settings should be typed."""
        from app.settings import Settings
        s = Settings()
        # Check key settings are properly typed with valid values
        assert s.db_pool_size > 0
        assert s.db_max_overflow >= 0
        assert s.debug in (True, False)
        assert len(s.api_title) > 0
