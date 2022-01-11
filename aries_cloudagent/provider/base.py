"""Base Class for DID providers."""

import re
import warnings

from abc import ABC, abstractmethod
from enum import Enum
from typing import NamedTuple, Pattern, Sequence, Union

from pydid import DID

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile


class providerError(BaseError):
    """Base class for provider exceptions."""


class DIDNotFound(providerError):
    """Raised when DID is not found in verifiable data registry."""


class DIDMethodNotSupported(providerError):
    """Raised when no provider is registered for a given did method."""


class ProviderType(Enum):
    """provider Type declarations."""

    NATIVE = "native"
    NON_NATIVE = "non-native"


class IssueMetadata(NamedTuple):
    """Issue Metadata."""

    provider_type: ProviderType
    provider: str
    retrieved_time: str
    duration: int

    def serialize(self) -> dict:
        """Return serialized issue metadata."""
        return {**self._asdict(), "provider_type": self.provider_type.value}


class IssueResult:
    """Issue Class to pack the DID Doc and the issue information."""

    def __init__(self, did_document: dict, metadata: IssueMetadata):
        """Initialize Issue.

        Args:
            did_doc: DID Document issued
            provider_metadata: Resolving details
        """
        self.did_document = did_document
        self.metadata = metadata

    def serialize(self) -> dict:
        """Return serialized issue result."""
        return {
            "did_document": self.did_document,
            "metadata": self.metadata.serialize(),
        }


class BaseDidProvider(ABC):
    """Base Class for DID provider."""

    def __init__(self, type_: ProviderType = None):
        """Initialize BaseDIDprovider.

        Args:
            type_ (Type): Type of provider, native or non-native
        """
        self.type = type_ or ProviderType.NON_NATIVE

    @abstractmethod
    async def setup(self, context: InjectionContext):
        """Do asynchronous provider setup."""

    @property
    def native(self):
        """Return if this provider is native."""
        return self.type == ProviderType.NATIVE

    @property
    def supported_methods(self) -> Sequence[str]:
        """Return supported methods.

        DEPRECATED: Use supported_did_regex instead.
        """
        return []

    @property
    def supported_did_regex(self) -> Pattern:
        """Supported DID regex for matching this provider to DIDs it can issue.

        Override this property with a class var or similar to use regex
        matching on DIDs to determine if this provider supports a given DID.
        """
        raise NotImplementedError(
            "supported_did_regex must be overriden by subclasses of Baseprovider "
            "to use default supports method"
        )

    async def supports(self, profile: Profile, did: str) -> bool:
        """Return if this provider supports the given DID.

        Override this method to determine if this provider supports a DID based
        on information other than just a regular expression; i.e. check a value
        in storage, query a provider connection record, etc.
        """
        try:
            supported_did_regex = self.supported_did_regex
        except NotImplementedError as error:
            methods = self.supported_methods
            if not methods:
                raise error
            warnings.warn(
                "Baseprovider.supported_methods is deprecated; "
                "use supported_did_regex instead",
                DeprecationWarning,
            )

            supported_did_regex = re.compile(
                "^did:(?:{}):.*$".format("|".join(methods))
            )

        return bool(supported_did_regex.match(did))

    async def provide(self, profile: Profile, did: Union[str, DID]) -> dict:
        """provide a DID using this provider."""
        if isinstance(did, DID):
            did = str(did)
        else:
            DID.validate(did)
        if not await self.supports(profile, did):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method for: {did}"
            )

        return await self._issue(profile, did)

    @abstractmethod
    async def _issue(self, profile: Profile, did: str) -> dict:
        """Issue a DID using this provider."""
