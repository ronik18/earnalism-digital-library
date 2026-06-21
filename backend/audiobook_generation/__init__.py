"""Dry-run audiobook generation interfaces for Earnalism."""

from .provider_adapter import (
    DryRunNarrationProvider,
    GenerationRequest,
    NarrationProvider,
    ProviderResult,
)

__all__ = [
    "DryRunNarrationProvider",
    "GenerationRequest",
    "NarrationProvider",
    "ProviderResult",
]
