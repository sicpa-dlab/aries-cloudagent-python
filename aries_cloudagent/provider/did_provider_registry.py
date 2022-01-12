"""In memory storage for registering did ledger."""

import logging
from typing import Sequence

from .base import BaseDidProvider

LOGGER = logging.getLogger(__name__)


class DIDProviderRegistry:
    """Registry for did providers."""

    def __init__(self):
        """Initialize list for did providers."""
        self._providers = []

    @property
    def providers(
        self,
    ) -> Sequence[BaseDidProvider]:
        """Accessor for a list of all did providers."""
        return self._providers

    def register(self, provider) -> None:
        """Register a provider."""
        LOGGER.debug("Registering provider %s", provider)
        self._resolvers.append(provider)
