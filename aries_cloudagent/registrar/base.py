"""Base Class for DID registrars."""

from abc import ABC, abstractmethod, abstractproperty
from distutils.log import error
from enum import Enum
import json
import logging
from typing import Optional

from aries_cloudagent.registrar.registration_result import RegistrationResult

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile
from .models.job import JobRecord


class RegistrarError(BaseError):
    """Base class for registrar exceptions."""


class DIDNotFound(RegistrarError):
    """Raised when DID is not found in verifiable data registry."""


class DIDMethodNotSupported(RegistrarError):
    """Raised when no registrar is registered for a given did method."""


class InvalidInput(RegistrarError):
    """Raised when invalid input is provided."""


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

    def __init__(self, type_: RegistrarType = None):
        """Initialize BaseDIDregistrar.

        Args:
            type_ (Type): Type of registrar, native or non-native
        """
        self.type = type_ or RegistrarType.EXTERNAL

    async def setup(self, context: InjectionContext):
        """Do asynchronous registrar setup."""
        logging.debug(
            "Setup from %s called with context: %s", self.__class__.__name__, context
        )

    @property
    @abstractmethod
    def method(self) -> str:
        """Return method handled by this registrar."""

    @property
    @abstractmethod
    def supported_key_types(self):
        """."""

    @abstractmethod
    async def create(
        self,
        profile: Profile,
        method: Optional[str],
        did: Optional[str],
        options: Optional[dict],
        secret: Optional[dict],
        document: dict,
    ) -> RegistrationResult:
        """Create a new DID."""

    @abstractmethod
    async def update(
        self,
        profile: Profile,
        did: str,
        options: Optional[dict],
        secret: Optional[dict],
        operation: list,
        document: dict,
    ) -> RegistrationResult:
        """Updates a did."""

    @abstractmethod
    async def deactivate(
        self,
        profile: Profile,
        did: str,
        options: Optional[dict],
        secret: Optional[dict],
    ) -> RegistrationResult:
        """Deactivates a did."""
