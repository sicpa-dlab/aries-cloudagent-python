"""Indy DID Registrar.

Resolution is performed using the IndyLedger class.
"""

from typing import Optional

from ...core.profile import Profile
from ..base import BaseDidRegistrar, RegistrarError, RegistrarType
from ..models.job import JobRecord


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
    ) -> JobRecord:
        """Create a DID from a given method."""
        return JobRecord()

    async def update(self, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        return JobRecord()

    async def deactivate(self, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        return JobRecord()
