"""OMR (Optical Music Recognition) service providers.

This module provides a pluggable architecture for OMR processing,
supporting multiple providers:
- MockProvider: For testing (instant results)
- AudiverisProvider: Open-source OMR via subprocess
- CommercialProvider: Placeholder for paid APIs (PlayScore, etc.)

Usage:
    from app.services.omr import get_omr_provider
    
    provider = get_omr_provider()
    result = await provider.process(file_path, options)
"""

from .base import OmrProvider, OmrProviderOptions, OmrProviderResult
from .factory import get_omr_provider
from .mock_provider import MockOmrProvider
from .audiveris_provider import AudiverisProvider

__all__ = [
    "OmrProvider",
    "OmrProviderOptions",
    "OmrProviderResult",
    "get_omr_provider",
    "MockOmrProvider",
    "AudiverisProvider",
]
