"""Base Class for DID registrars."""

import logging

from abc import ABC, abstractmethod
from enum import Enum
from typing import NamedTuple, Optional, Pattern

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
    """Registrar type declarations.

    INTERNAL mode refers to when secrets are stored within this ACA-Py instance's
    currently loaded secret storage system (Indy SDK Wallet, Askar, etc.)

    HYBRID mode refers to when secrets are accessible to this ACA-Py instance
    but not stored within ACA-Py's secret storage system.

    EXTERNAL mode refers to when secrets are held outside of this ACA-Py
    Instance altogether and are not accessible directly.
    """

    INTERNAL = "internal-secret-mode"
    HYBRID = "hybrid-secret-mode"
    EXTERNAL = "external-secret-mode"


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

    async def setup(self, context: InjectionContext):
        """Do asynchronous registrar setup."""
        logging.debug(
            "Setup from %s called with context: %s", self.__class__.__name__, context
        )

    @abstractmethod
    async def create(
        self, profile, method, did, options, secret, didDocument
    ) -> Optional[
        dict
    ]:  # jobId, didState, didRegistrationMetadata, didDocumentMetadata:
        """Create a new DID."""

    @abstractmethod
    async def ready_to_register() -> bool:
        """Check if DID is ready to be registered."""

    @abstractmethod
    async def register(self, profile, did, document):
        """Register the DID as defined by the DID method."""

    async def create_and_register(self, profile, did, document):
        """Create and register a DID."""
        raise NotImplementedError("Not supported for this DID Method.")

    @abstractmethod
    async def update(
        did, options, secret, didDocumentOperation, didDocument
    ) -> Optional[
        dict
    ]:  # jobId, didState, didRegistrationMetadata, didDocumentMetadata:
        """Updates a did"""

    @abstractmethod
    async def deactivate(
        did, options, secret
    ) -> Optional[
        dict
    ]:  # jobId, didState, didRegistrationMetadata, didDocumentMetadata:
        """Deactivates a did"""

    @abstractmethod
    def supported_did_regex(self) -> Pattern:
        """Supported DID regex for matching this registrar to DIDs it can issue.

        Override this property with a class var or similar to use regex
        matching on DIDs to determine if this registrar supports a given DID.
        """

    @abstractmethod
    async def supports(self, profile: Profile, did: str) -> bool:
        """Return if this registrar supports the given DID.

        Override this method to determine if this registrar supports a DID based
        on information other than just a regular expression; i.e. check a value
        in storage, query a registrar connection record, etc.
        """
