"""Indy DID Registrar.

Resolution is performed using the IndyLedger class.
"""

from typing import Optional


from ...core.profile import Profile

from ..base import (
    BaseDidRegistrar,
    RegistrarType,
    RegistrarError,
)


class NoIndyLedger(RegistrarError):
    """Raised when there is no Indy ledger instance configured."""


class IndyDIDRegistrar(BaseDidRegistrar):
    """Indy DID Registrar."""

    AGENT_SERVICE_TYPE = "did-communication"

    def __init__(self):
        """Initialize Indy Registrar."""
        super().__init__(RegistrarType.INTERNAL)

    async def create(
        self,
        profile: Profile,
        method: Optional[str] = None,
        did: Optional[str] = None,
        document: Optional[dict] = None,
        **options: dict
    ) -> Optional[dict]:
        """Create a DID from a given method."""

    async def ready_to_register(self) -> bool:
        """Determine if DID is ready to register."""

    async def register(self, profile: Profile, did: str, document: dict):
        """Register DID."""

    async def update(self, did: str, document: dict, **options: dict) -> Optional[dict]:
        """Update DID."""

    async def deactivate(self, did: str, **options: dict) -> Optional[dict]:
        """Deactivate DID."""
