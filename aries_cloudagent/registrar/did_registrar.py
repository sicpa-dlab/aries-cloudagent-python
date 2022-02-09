"""
the did registrar.

responsible for keeping track of all registrars. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from typing import Optional, Sequence

from ..core.profile import Profile
from .base import BaseDidRegistrar
from .models.job import JobRecord
from pydid.did import DID

LOGGER = logging.getLogger(__name__)


class DIDRegistrar(BaseDidRegistrar):
    """did registrar singleton."""

    def __init__(self, registrars: Sequence[BaseDidRegistrar] = None):
        """Create DID registrar."""
        self.method_to_registrar = {
            registrar.method: registrar for registrar in registrars or []
        }

    def register_registrar(self, registrar: BaseDidRegistrar):
        """Register a new registrar."""
        self.method_to_registrar[registrar.method] = registrar

    async def create(
        self,
        profile: Profile,
        method: Optional[str] = None,
        did: Optional[str] = None,
        document: Optional[dict] = None,
        **options: str
    ) -> JobRecord:
        """Create a DID from a given method."""
        # TODO: method should not need to be passed into create...
        if not method and not did:
            raise ValueError("Either did or method must be provided")

        if not method and did:
            method = DID(did).method

        if not method:
            raise ValueError("Either did or method must be provided")

        return await self.method_to_registrar[method].create(
            profile, method, did, document, **options
        )

    async def update(self, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        return JobRecord()

    async def deactivate(self, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        return JobRecord()
