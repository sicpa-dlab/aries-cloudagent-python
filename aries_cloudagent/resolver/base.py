"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence, Union
import re

from pydid import DID, DIDDocument

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile


class ResolverError(BaseError):
    """Base class for resolver exceptions."""


class DIDNotFound(ResolverError):
    """Raised when DID is not found in verifiable data registry."""


class DIDMethodNotSupported(ResolverError):
    """Raised when no resolver is registered for a given did method."""


class ResolverType(Enum):
    """Resolver Type declarations."""

    NATIVE = "native"
    NON_NATIVE = "non-native"
    supported_did_regex = None

class BaseDIDResolver(ABC):
    """Base Class for DID Resolvers."""

    def __init__(self, type_: ResolverType = None):
        """Initialize BaseDIDResolver.

        Args:
            type_ (Type): Type of resolver, native or non-native
        """
        self.type = type_ or ResolverType.NON_NATIVE

    @abstractmethod
    async def setup(self, context: InjectionContext):
        """Do asynchronous resolver setup."""

    @property
    def native(self):
        """Return if this resolver is native."""
        return self.type == ResolverType.NATIVE

    @property
    @abstractmethod
    def supported_did_regex(self):
        """Regex of DID methods supported by this resolver."""
        raise NotImplementedError()

    async def supports(self, profile: Profile, did: str) -> bool:
        """Return if this resolver supports the given method."""
        method_pattern = re.compile(self.supported_did_regex)
        return bool(method_pattern.match(did))

    async def resolve(self, profile: Profile, did: Union[str, DID]) -> DIDDocument:
        """Resolve a DID using this resolver."""
        py_did = DID(did) if isinstance(did, str) else did

        if not await self.supports(profile, py_did.method):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method {py_did.method}"
            )

        did_document = await self._resolve(profile, str(py_did))
        result = DIDDocument.deserialize(did_document)
        return result

    @abstractmethod
    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve a DID using this resolver."""
