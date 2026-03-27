"""OMR provider factory.

Creates the appropriate OMR provider based on application settings.
"""

import logging
from typing import Optional

from app.settings import settings
from .base import OmrProvider, OmrProviderType
from .mock_provider import MockOmrProvider
from .audiveris_provider import AudiverisProvider
from .oemer_provider import OemerProvider

logger = logging.getLogger(__name__)

# Singleton cache for providers
_provider_cache: dict[str, OmrProvider] = {}


def get_omr_provider(
    provider_type: Optional[str] = None,
    *,
    force_new: bool = False,
) -> OmrProvider:
    """Get an OMR provider instance.

    Args:
        provider_type: Provider type to use. If None, uses settings.omr_provider.
        force_new: If True, create a new instance instead of using cache.

    Returns:
        An OmrProvider instance

    Raises:
        ValueError: If the provider type is unknown
    """
    provider_type = provider_type or settings.omr_provider

    # Return cached instance if available
    if not force_new and provider_type in _provider_cache:
        return _provider_cache[provider_type]

    # Create provider based on type
    provider = _create_provider(provider_type)

    # Cache for reuse
    _provider_cache[provider_type] = provider

    return provider


def _create_provider(provider_type: str) -> OmrProvider:
    """Create a new provider instance."""
    try:
        ptype = OmrProviderType(provider_type.lower())
    except ValueError:
        raise ValueError(
            f"Unknown OMR provider: '{provider_type}'. "
            f"Valid options: {[t.value for t in OmrProviderType]}"
        )

    if ptype == OmrProviderType.MOCK:
        logger.info("Using MockOmrProvider")
        return MockOmrProvider()

    if ptype == OmrProviderType.AUDIVERIS:
        logger.info("Using AudiverisProvider with path: %s", settings.audiveris_path or "auto-detect")
        provider: OmrProvider = AudiverisProvider(
            audiveris_path=settings.audiveris_path or None,
            java_path=settings.audiveris_java_path,
        )
        if not provider.is_available:
            logger.warning(
                "Audiveris is not available. "
                "Run scripts/setup_omr.sh to install it."
            )
        return provider

    if ptype == OmrProviderType.OEMER:
        logger.info("Using OemerProvider")
        provider = OemerProvider()
        if not provider.is_available:
            logger.warning(
                "oemer is not available. "
                "Install it with: pip install oemer"
            )
        return provider

    if ptype == OmrProviderType.COMMERCIAL:
        # Placeholder for commercial API integration
        logger.warning(
            "Commercial OMR provider not yet implemented, falling back to mock"
        )
        return MockOmrProvider()

    # Should not reach here due to enum validation
    raise ValueError(f"Unhandled provider type: {ptype}")


def list_available_providers() -> dict[str, bool]:
    """List all providers and their availability status.

    Returns:
        Dict mapping provider name to availability boolean
    """
    availability = {}

    # Check each provider type
    for ptype in OmrProviderType:
        try:
            provider = get_omr_provider(ptype.value, force_new=True)
            availability[ptype.value] = provider.is_available
        except Exception:
            availability[ptype.value] = False

    return availability


async def get_provider_versions() -> dict[str, Optional[str]]:
    """Get version strings for all available providers.

    Returns:
        Dict mapping provider name to version string (or None if unavailable)
    """
    versions = {}

    for ptype in OmrProviderType:
        try:
            provider = get_omr_provider(ptype.value, force_new=True)
            if provider.is_available:
                versions[ptype.value] = await provider.get_version()
            else:
                versions[ptype.value] = None
        except Exception:
            versions[ptype.value] = None

    return versions
