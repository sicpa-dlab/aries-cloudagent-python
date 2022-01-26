"""
the did registrar.

responsible for keeping track of all registrars. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from typing import Sequence, Optional

from ..core.profile import Profile
from .base import BaseDidRegistrar

LOGGER = logging.getLogger(__name__)


class DIDRegistrar(BaseDidRegistrar):
    """did registrar singleton."""

    def __init__(self, registrars: Sequence[BaseDidRegistrar]):
        """Create DID registrar."""
        self.registrars = registrars

    async def create(
        self,
        profile: Profile,
        method: Optional[str] = None,
        did: Optional[str] = None,
        document: Optional[dict] = None,
        **options: dict
    ) -> Optional[dict]:
        """Create a DID from a given method."""

    async def ready_to_register(self) -> bool:
        """Determine if DID is ready to register."""

    async def register(self, profile: Profile, did: str, document: dict):
        """Register DID."""

    async def update(self, did: str, document: dict, **options: dict) -> Optional[dict]:
        """Update DID."""

    async def deactivate(self, did: str, **options: dict) -> Optional[dict]:
        """Deactivate DID."""
