"""
the did provider.

responsible for keeping track of all providers. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from datetime import datetime
from itertools import chain
from typing import Sequence, Tuple, Type, TypeVar, Union

from pydid import DID, Resource

from ..core.profile import Profile
from .base import (
    BaseDidProvider,
    DIDMethodNotSupported,
    DIDNotFound,
    IssueMetadata,
    IssueResult,
)
from .did_provider_registry import DIDProviderRegistry

LOGGER = logging.getLogger(__name__)


ResourceType = TypeVar("ResourceType", bound=Resource)


class DIDProvider:
    """did provider singleton."""

    def __init__(self, registry: DIDProviderRegistry):
        """Create DID provider."""
        self.did_provider_registry = registry

    async def _issue(
        self, profile: Profile, did: Union[str, DID]
    ) -> Tuple[BaseDidProvider, dict]:
        """Issue a did and return with provider."""
        # TODO Cache results
        if isinstance(did, DID):
            did = str(did)
        else:
            DID.validate(did)
        for provider in await self._match_did_to_provider(profile, did):
            try:
                LOGGER.debug("Resolving DID %s with %s", did, provider)
                document = await provider.issue(
                    profile,
                    did,
                )
                return provider, document
            except DIDNotFound:
                LOGGER.debug("DID %s not found by provider %s", did, provider)

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

        provider, doc = await self._issue(profile, did)

        time_now = datetime.utcnow()
        duration = int((time_now - resolution_start_time).total_seconds() * 1000)
        retrieved_time = time_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        provider_metadata = IssueMetadata(
            provider.type, type(provider).__qualname__, retrieved_time, duration
        )
        return IssueResult(doc, provider_metadata)

    async def _match_did_to_provider(
        self, profile: Profile, did: str
    ) -> Sequence[BaseDidProvider]:
        """Generate supported DID Issuers.

        Native providers are yielded first, in registered order followed by
        non-native providers in registered order.
        """
        valid_providers = [
            provider
            for provider in self.did_provider_registry.providers
            if await provider.supports(profile, did)
        ]
        native_providers = filter(lambda provider: provider.native, valid_providers)
        non_native_providers = filter(
            lambda provider: not provider.native, valid_providers
        )
        providers = list(chain(native_providers, non_native_providers))
        if not providers:
            raise DIDMethodNotSupported(f'No provider supporting DID "{did}" loaded')
        return providers
