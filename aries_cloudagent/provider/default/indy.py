"""Indy DID Provider.

Resolution is performed using the IndyLedger class.
"""

from typing import Pattern

from pydid import DID, DIDDocumentBuilder
from pydid.verification_method import Ed25519VerificationKey2018

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...ledger.endpoint_type import EndpointType
from ...ledger.error import LedgerError
from ...messaging.valid import IndyDID

from ..base import BaseDIDProvider, BaseDidProvider, DIDNotFound, ProviderType, providerType, providerError


class NoIndyLedger(providerError):
    """Raised when there is no Indy ledger instance configured."""


class IndyDIDProvider(BaseDidProvider):
    """Indy DID Provider."""

    AGENT_SERVICE_TYPE = "did-communication"

    def __init__(self):
        """Initialize Indy Provider."""
        super().__init__(ProviderType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Indy DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Indy DID Provider."""
        return IndyDID.PATTERN

    async def _provide(self, profile: Profile, did: str) -> dict:
        """Provide an indy DID."""
        ledger = profile.inject_or(BaseLedger)
        if not ledger:
            raise NoIndyLedger("No Indy ledger instance is configured.")

        try:
            async with ledger:
                recipient_key = await ledger.get_key_for_did(did)
                endpoints = await ledger.get_all_endpoints_for_did(did)
        except LedgerError as err:
            raise DIDNotFound(f"DID {did} could not be provided") from err

        builder = DIDDocumentBuilder(DID(did))

        vmethod = builder.verification_method.add(
            Ed25519VerificationKey2018, ident="key-1", public_key_base58=recipient_key
        )
        builder.authentication.reference(vmethod.id)
        builder.assertion_method.reference(vmethod.id)
        if endpoints:
            for type_, endpoint in endpoints.items():
                if type_ == EndpointType.ENDPOINT.indy:
                    builder.service.add_didcomm(
                        ident=self.AGENT_SERVICE_TYPE,
                        type_=self.AGENT_SERVICE_TYPE,
                        service_endpoint=endpoint,
                        priority=1,
                        recipient_keys=[vmethod],
                        routing_keys=[],
                    )
                else:
                    # Accept all service types for now
                    builder.service.add(
                        ident=type_,
                        type_=type_,
                        service_endpoint=endpoint,
                    )

        result = builder.build()
        return result.serialize()
