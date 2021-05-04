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


class ResolverDriver(Enum):
    """Resolver Type declarations."""

    HTTP_DRIVER = "HttpDriver"


class Resolution:
    """Resolution Class to pack the DID Doc and the resolution information."""

    def __init__(self, did_doc: DIDDocument, resolver_metadata: dict):
        """Initialize Resolution.

        Args:
            did_doc: DID Document resolved
            resolver_metadata: Resolving details
        """
        self.did_doc = did_doc
        self.resolver_metadata = resolver_metadata


class BaseDIDResolver(ABC):
    """Base Class for DID Resolvers."""

    def __init__(self, type_: ResolverType = None, driver: ResolverDriver = None):
        """Initialize BaseDIDResolver.

        Args:
            type_ (Type): Type of resolver, native or non-native
        """
        self.type = type_ or ResolverType.NON_NATIVE
        self.driver = driver or ResolverDriver.HTTP_DRIVER

    @abstractmethod
    async def setup(self, context: InjectionContext):
        """Do asynchronous resolver setup."""

    @property
    def native(self):
        """Return if this resolver is native."""
        return self.type == ResolverType.NATIVE

    @property
    @abstractmethod
    def supported_methods(self) -> Sequence[str]:
        """Return list of DID methods supported by this resolver."""

    def supports(self, did: Union[str, DID]) -> bool:
        """Return if this resolver supports the given method."""
        if isinstance(did, DID):
            did = str(did)

        for method in self.supported_methods:
            method_pattern = re.compile(f"did:{method}:.*")
            if method_pattern.match(did):
                return True

        return False

    async def resolve(self, profile: Profile, did: Union[str, DID]) -> Resolution:
        """Resolve a DID using this resolver."""
        py_did = DID(did) if isinstance(did, str) else did

        if not self.supports(py_did):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method {py_did.method}"
            )
        previous_time = datetime.utcnow()
        did_document = await self._resolve(profile, str(py_did))
        resolver_metadata = self._retrieve_resolver_metadata(
            py_did.method, previous_time
        )
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
        return Resolution(result, resolver_metadata)

    @abstractmethod
    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve a DID using this resolver."""

    def _retrieve_resolver_metadata(self, method, previous_time):

        time_now = datetime.utcnow()
        time_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        duration = int((time_now - previous_time).total_seconds() * 1000)
        resolver_metadata = {
            "type": self.type,
            "driverId": f"did:{method}",
            "driver": self.driver,
            "retrieved": time_now,
            "duration": duration,
        }

        return resolver_metadata
