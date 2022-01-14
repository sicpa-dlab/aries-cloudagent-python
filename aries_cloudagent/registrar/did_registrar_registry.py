"""In memory storage for registering did ledger."""

import logging
from typing import Sequence

from .base import BaseDidRegistrar

LOGGER = logging.getLogger(__name__)


class DIDRegistrarRegistry:
    """Registry for did registrars."""

    def __init__(self):
        """Initialize list for did registrars."""
        self._registrars = []

    @property
    def registrars(
        self,
    ) -> Sequence[BaseDidRegistrar]:
        """Accessor for a list of all did registrars."""
        return self._registrars

    def register(self, registrar) -> None:
        """Register a registrar."""
        LOGGER.debug("Registering registrar %s", registrar)
        self._registrars.append(registrar)
