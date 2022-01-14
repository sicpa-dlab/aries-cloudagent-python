"""
the did registrar.

responsible for keeping track of all registrars. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from datetime import datetime
from itertools import chain
from typing import Sequence, Tuple, TypeVar, Union

from pydid import DID, Resource

from ..core.profile import Profile
from .base import (
    BaseDidRegistrar,
    DIDMethodNotSupported,
    DIDNotFound,
    IssueMetadata,
    IssueResult,
)
from .did_registrar_registry import DIDRegistrarRegistry

LOGGER = logging.getLogger(__name__)


ResourceType = TypeVar("ResourceType", bound=Resource)


class DIDRegistrar:
    """did registrar singleton."""

    def __init__(self, registry: DIDRegistrarRegistry):
        """Create DID registrar."""
        self.did_registrar_registry = registry

    async def _issue(
        self, profile: Profile, did: Union[str, DID]
    ) -> Tuple[BaseDidRegistrar, dict]:
        """Issue a did and return with registrar."""
        # TODO Cache results
        if isinstance(did, DID):
            did = str(did)
        else:
            DID.validate(did)
        for registrar in await self._match_did_to_registrar(profile, did):
            try:
                LOGGER.debug("Resolving DID %s with %s", did, registrar)
                document = await registrar.issue(
                    profile,
                    did,
                )
                return registrar, document
            except DIDNotFound:
                LOGGER.debug("DID %s not found by registrar %s", did, registrar)

        raise DIDNotFound(f"DID {did} could not be issued")

    async def issue(self, profile: Profile, did: Union[str, DID]) -> dict:
        """Issue a DID."""
        _, doc = await self._issue(profile, did)
        return doc

    async def issue_with_metadata(
        self, profile: Profile, did: Union[str, DID]
    ) -> IssueResult:
        """Issue a DID and return the IssueResult."""
        resolution_start_time = datetime.utcnow()

        registrar, doc = await self._issue(profile, did)

        time_now = datetime.utcnow()
        duration = int((time_now - resolution_start_time).total_seconds() * 1000)
        retrieved_time = time_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        registrar_metadata = IssueMetadata(
            registrar.type, type(registrar).__qualname__, retrieved_time, duration
        )
        return IssueResult(doc, registrar_metadata)

    async def _match_did_to_registrar(
        self, profile: Profile, did: str
    ) -> Sequence[BaseDidRegistrar]:
        """Generate supported DID Issuers.

        Native registrars are yielded first, in registered order followed by
        non-native registrars in registered order.
        """
        valid_registrars = [
            registrar
            for registrar in self.did_registrar_registry.registrars
            if await registrar.supports(profile, did)
        ]
        native_registrars = filter(lambda registrar: registrar.native, valid_registrars)
        non_native_registrars = filter(
            lambda registrar: not registrar.native, valid_registrars
        )
        registrars = list(chain(native_registrars, non_native_registrars))
        if not registrars:
            raise DIDMethodNotSupported(f'No registrar supporting DID "{did}" loaded')
        return registrars
