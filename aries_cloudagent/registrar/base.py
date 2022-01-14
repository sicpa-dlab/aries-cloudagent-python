"""Base Class for DID registrars."""

import logging
import re
import warnings

from abc import ABC, abstractmethod
from enum import Enum
from typing import NamedTuple, Optional, Pattern, Sequence

from pydid import DID

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile


class RegistrarError(BaseError):
    """Base class for registrar exceptions."""


class DIDNotFound(RegistrarError):
    """Raised when DID is not found in verifiable data registry."""


class DIDMethodNotSupported(RegistrarError):
    """Raised when no registrar is registered for a given did method."""


class RegistrarType(Enum):
    """registrar Type declarations."""

    INTERNAL = "internal-secret-mode"
    EXTERNAL = "external-secret-mode"
    CLIENT = "client-managed-secret-mode"


class IssueMetadata(NamedTuple):
    """Issue Metadata."""

    registrar_type: RegistrarType
    registrar: str
    retrieved_time: str
    duration: int

    def serialize(self) -> dict:
        """Return serialized issue metadata."""
        return {**self._asdict(), "registrar_type": self.registrar_type.value}


class IssueResult:
    """Issue Class to pack the DID Doc and the issue information."""

    def __init__(self, did_document: dict, metadata: IssueMetadata):
        """Initialize Issue.

        Args:
            did_doc: DID Document issued
            registrar_metadata: Resolving details
        """
        self.did_document = did_document
        self.metadata = metadata

    def serialize(self) -> dict:
        """Return serialized issue result."""
        return {
            "did_document": self.did_document,
            "metadata": self.metadata.serialize(),
        }


class BaseDidRegistrar(ABC):
    """Base Class for DID registrar."""

    def __init__(self, type_: RegistrarType = None, storing=None, returning=None):
        """Initialize BaseDIDregistrar.

        Args:
            type_ (Type): Type of registrar, native or non-native
        """
        self.type = type_ or RegistrarType.EXTERNAL
        self.default_secret_storing = storing
        self.default_secret_returning = returning

    @abstractmethod
    async def setup(self, context: InjectionContext):
        """Do asynchronous registrar setup."""
        logging.info("setup called in did registry")

    @property
    def internal(self):
        """Return if this registrar is internal mode."""
        return self.type == RegistrarType.INTERNAL

    @property
    async def create(
        self, profile, method, did, options, secret, didDocument
    ) -> Optional[
        dict
    ]:  # jobId, didState, didRegistrationMetadata, didDocumentMetadata:
        """Creates a new did"""
        if isinstance(did, DID):
            did = str(did)
        else:
            DID.validate(did)
        if not await self.supports(profile, did):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method for: {did}"
            )

        return await self._issue(profile, did)

    @property
    def update(
        did, options, secret, didDocumentOperation, didDocument
    ) -> Optional[
        dict
    ]:  # jobId, didState, didRegistrationMetadata, didDocumentMetadata:
        """Updates a did"""

    @property
    def deactivate(
        did, options, secret
    ) -> Optional[
        dict
    ]:  # jobId, didState, didRegistrationMetadata, didDocumentMetadata:
        """Deactivates a did"""

    @property
    def supported_methods(self) -> Sequence[str]:
        """Return supported methods.

        DEPRECATED: Use supported_did_regex instead.
        """
        return []

    @property
    def supported_did_regex(self) -> Pattern:
        """Supported DID regex for matching this registrar to DIDs it can issue.

        Override this property with a class var or similar to use regex
        matching on DIDs to determine if this registrar supports a given DID.
        """
        raise NotImplementedError(
            "supported_did_regex must be overriden by subclasses of Baseregistrar "
            "to use default supports method"
        )

    async def supports(self, profile: Profile, did: str) -> bool:
        """Return if this registrar supports the given DID.

        Override this method to determine if this registrar supports a DID based
        on information other than just a regular expression; i.e. check a value
        in storage, query a registrar connection record, etc.
        """
        try:
            supported_did_regex = self.supported_did_regex
        except NotImplementedError as error:
            methods = self.supported_methods
            if not methods:
                raise error
            warnings.warn(
                "Baseregistrar.supported_methods is deprecated; "
                "use supported_did_regex instead",
                DeprecationWarning,
            )

            supported_did_regex = re.compile(
                "^did:(?:{}):.*$".format("|".join(methods))
            )

        return bool(supported_did_regex.match(did))

    @abstractmethod
    async def _issue(self, profile: Profile, did: str) -> dict:
        """Issue a DID using this registrar."""
