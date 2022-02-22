"""
the did registrar.

responsible for keeping track of all registrars. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from ast import Str
from typing import Dict, Optional

from pydid.did import DID

from ..core.profile import Profile
from .base import BaseDidRegistrar
from .models.job import JobRecord

LOGGER = logging.getLogger(__name__)


class DIDRegistrars:
    """did registrar singleton."""

    def __init__(self):
        """Create DID registrar."""
        self.method_to_registrar: Dict[Str, BaseDidRegistrar] = {}
        
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
        if not method and not did:
            raise ValueError("Either did or method must be provided")

        if not method:
            method = DID(did).method

        if not method:
            raise ValueError("Either did or method must be provided")
        
        if self.method_to_registrar and method not in self.method_to_registrar.keys():
            raise ValueError("No registrar for method", method)

        # TODO: method should not need to be passed into create...
        return await self.method_to_registrar[method].create(
            profile, method, did, document, **options
        )

    async def update(self, profile: Profile, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        if not document and not did:
            raise ValueError("did and document must be provided")
        method = did.split(":")[1] # TODO: use did lib to do this
        
        if self.method_to_registrar and method not in self.method_to_registrar.keys():
            raise ValueError("No registrar for method", method)
        
        return await self.method_to_registrar[method].update(profile, did, document, **options)

    async def deactivate(self, profile: Profile, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        if not did:
            raise ValueError("did must be provided")
        method = did.split(":")[1] # TODO: use did lib to do this
        
        if self.method_to_registrar and method not in self.method_to_registrar.keys():
            raise ValueError("No registrar for method", method)
        
        return await self.method_to_registrar[method].deactivate(profile, did, **options)
