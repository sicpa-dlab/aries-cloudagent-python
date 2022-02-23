"""Indy DID Registrar.

Resolution is performed using the IndyLedger class.
"""

from typing import Optional

from ...core.profile import Profile
from ..base import BaseDidRegistrar, RegistrarType
from ..models.job import JobRecord


class IndyDIDRegistrar(BaseDidRegistrar):
    """Indy DID Registrar."""

    AGENT_SERVICE_TYPE = "did-communication"

    def __init__(self):
        """Initialize Indy Registrar."""
        super().__init__(RegistrarType.INTERNAL)
        self.method = "sov"

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, value):
        self._method = value

    async def create(
        self,
        profile: Profile,
        method: Optional[str],
        did: Optional[str] = None,
        document: Optional[dict] = None,
        **options: dict,
    ) -> JobRecord:
        """Create a DID from a given method."""
        raise NotImplementedError()

    async def update(self, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        raise NotImplementedError()

    async def deactivate(self, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        raise NotImplementedError()
