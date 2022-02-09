"""
the did registrar.

responsible for keeping track of all registrars. more importantly
writting did's to different sources provided by the method type.
"""

import logging
from typing import Dict, Optional, Pattern, Sequence

from aries_cloudagent.holder.routes import register

from ..core.profile import Profile
from .base import BaseDidRegistrar
from .models.job import JobRecord

LOGGER = logging.getLogger(__name__)

class DIDRegistrar(BaseDidRegistrar):
    """did registrar singleton."""

    def __init__(self, registrars: Dict[Pattern, BaseDidRegistrar]):
        """Create DID registrar."""
        self.registrars = registrars

    async def create(
        self,
        profile: Profile,
        method: Optional[str] = None,
        did: Optional[str] = None,
        document: Optional[dict] = None,
        **options: dict
    ) -> JobRecord:
        """Create a DID from a given method."""
        # TODO: method should not need ot be passed into create...
        return self.registrars[method].create(profile,method,did,document)

    async def update(self, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        return JobRecord()

    async def deactivate(self, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        return JobRecord()
