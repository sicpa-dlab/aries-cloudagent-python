"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence, Union
from datetime import datetime
import re

from pydid import DID, DIDDocument
from pydid.options import (
    doc_allow_public_key,
    doc_insert_missing_ids,
    vm_allow_controller_list,
    vm_allow_missing_controller,
    vm_allow_type_list,
)
from collections import namedtuple
from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile

ResolverMetadata = namedtuple(
    "resolver_metadata", ["type", "driverId", "resolver", "retrieved", "duration"]
)


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


class ResolutionResult:
    """Resolution Class to pack the DID Doc and the resolution information."""

    def __init__(self, did_doc: DIDDocument, metadata: ResolverMetadata = None):
        """Initialize Resolution.

        Args:
            did_doc: DID Document resolved
            resolver_metadata: Resolving details
        """
        self.did_doc = did_doc
        self.metadata = metadata


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
    def supported_methods(self) -> Sequence[str]:
        """Return list of DID methods supported by this resolver."""
        raise NotImplementedError()

    async def supports(self, profile: Profile, did: Union[str, DID]) -> bool:
        """Return if this resolver supports the given method."""
        if isinstance(did, DID):
            did = str(did)

        for method in self.supported_methods:
            method_pattern = re.compile(f"did:{method}:.*")
            if method_pattern.match(did):
                return True

        return False

    async def resolve(
        self, profile: Profile, did: Union[str, DID], retrieve_metadata: bool = False
    ) -> ResolutionResult:
        """Resolve a DID using this resolver."""

        async def resolve_with_metadata(py_did):
            resolution_start_time = datetime.utcnow()

            did_document = await self._resolve(profile, str(py_did))

            resolver_metadata = await self._retrieve_resolver_metadata(
                py_did.method, resolution_start_time
            )

            return did_document, resolver_metadata

        py_did = DID(did) if isinstance(did, str) else did

        if not await self.supports(profile, py_did):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method {py_did.method}"
            )
        if retrieve_metadata:
            did_document, resolver_metadata = await resolve_with_metadata(py_did)

        else:
            did_document = await self._resolve(profile, str(py_did))
            resolver_metadata = None

        result = DIDDocument.deserialize(
            did_document,
            options={
                doc_insert_missing_ids,
                doc_allow_public_key,
                vm_allow_controller_list,
                vm_allow_missing_controller,
                vm_allow_type_list,
            },
        )
        return ResolutionResult(result, resolver_metadata)

    @abstractmethod
    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve a DID using this resolver."""

    async def _retrieve_resolver_metadata(self, method, resolution_start_time):

        time_now = datetime.utcnow()
        duration = int((time_now - resolution_start_time).total_seconds() * 1000)
        retrieved_time = time_now.strftime("%Y-%m-%dT%H:%M:%SZ")

        internal_class = self.__class__
        module = internal_class.__module__
        class_name = internal_class.__qualname__
        resolver = module + "." + class_name

        resolver_metadata = ResolverMetadata(
            self.type.value, f"did:{method}", resolver, retrieved_time, duration
        )

        return resolver_metadata
