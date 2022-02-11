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

        if not method:
            method = DID(did).method

        if not method:
            raise ValueError("Either did or method must be provided")

        return await self.method_to_registrar[method].create(
            profile, method, did, document, **options
        )

    async def update(self, profile: Profile, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        if not document and not did:
            raise ValueError("did and document must be provided")
        method = did.split(":")[1] # TODO: use did lib to do this
        return await self.method_to_registrar[method].update(profile, did, document, **options)

    async def deactivate(self, profile: Profile, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        if not did:
            raise ValueError("did must be provided")
        method = did.split(":")[1] # TODO: use did lib to do this
        return await self.method_to_registrar[method].deactivate(profile, did, **options)
