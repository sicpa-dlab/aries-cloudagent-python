"""
the did registrar.

responsible for keeping track of all registrars. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from typing import Dict, Optional

from pydid.did import DID

from aries_cloudagent.registrar.registration_result import RegistrationResult

from ..core.profile import Profile
from .base import BaseDidRegistrar, DIDMethodNotSupported, InvalidInput
from .models.job import JobRecord

LOGGER = logging.getLogger(__name__)


class DIDRegistrars:
    """did registrar singleton."""

    def __init__(self):
        """Create DID registrar."""
        self.method_to_registrar: Dict[str, BaseDidRegistrar] = {}

    def register_registrar(self, registrar: BaseDidRegistrar):
        """Register a new registrar."""
        self.method_to_registrar[registrar.method] = registrar

    async def create(
        self,
        profile: Profile,
        method: Optional[str],
        did: Optional[str],
        options: Optional[dict],
        secret: Optional[dict],
        document: dict,
    ) -> RegistrationResult:
        """Create a DID from a given method."""
        if method and did:
            # TODO: better to check if method matches did method
            raise InvalidInput("method and did must be 'exclusive or'")
        if not method and not did:
            raise InvalidInput("Either did or method must be provided")
        if not document:
            raise InvalidInput("document is required")
        if not method:
            assert did
            method = DID(did).method

        if self.method_to_registrar and method not in self.method_to_registrar:
            raise DIDMethodNotSupported("No registrar for method", method)

        return await self.method_to_registrar[method].create(
            profile, method, did, options, secret, document
        )

    async def update(
        self,
        profile: Profile,
        did: str,
        options: Optional[dict],
        secret: Optional[dict],
        operation: list,
        document: dict,
    ) -> JobRecord:
        """Update DID."""
        if not did:
            raise InvalidInput("did is required for updates")
        if operation and (not operation.isinstance(list)):
            raise InvalidInput("operations must be a list")
        else:
            operation = ["setDidDocument"]
        if not document:
            raise InvalidInput("document is required for updates")

        method = did.split(":")[1]  # TODO: use did lib to do this

        if self.method_to_registrar and method not in self.method_to_registrar:
            raise DIDMethodNotSupported("No registrar for method", method)

        return await self.method_to_registrar[method].update(
            profile, did, options, secret, operation, document
        )

    async def deactivate(
        self,
        profile: Profile,
        did: str,
        options: Optional[dict],
        secret: Optional[dict],
    ) -> JobRecord:
        """Deactivate DID."""
        if not did:
            raise InvalidInput("did is required for deactivate")
        method = did.split(":")[1]  # TODO: use did lib to do this

        if self.method_to_registrar and method not in self.method_to_registrar:
            raise DIDMethodNotSupported("No registrar for method", method)

        return await self.method_to_registrar[method].deactivate(
            profile, did, options, secret
        )
