"""
the did registrar.

responsible for keeping track of all registrars. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from typing import Sequence, Optional

from ..core.profile import Profile
from .base import BaseDidRegistrar
from .models.job import JobRecord

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
    ) -> JobRecord:
        """Create a DID from a given method."""

    async def update(self, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""

    async def deactivate(self, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
