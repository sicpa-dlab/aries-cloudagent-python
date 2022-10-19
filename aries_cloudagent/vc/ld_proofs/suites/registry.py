"""Signature Suite Registry."""


from typing import Dict, Sequence, Set, Type


from ....did.did_key import DIDKey
from ....wallet.did_info import DIDInfo
from ....vc.ld_proofs import (
    Ed25519Signature2018,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
    WalletKeyPair,
    JwsLinkedDataSignature,
)
from ....wallet.base import BaseWallet
from ....core.error import BaseError

from ....wallet.key_type import KeyType
from .linked_data_proof import LinkedDataProof


class CredFormatError(BaseError):
    """Credential format error under issue-credential protocol v2.0."""


class LDProofSuiteRegistryError(Exception):
    """Generic LDProofSuiteRegistry Error."""


class UnsupportedProofType(LDProofSuiteRegistryError):
    """Raised when proof type is not supported by registered suites."""


class LDProofSuiteRegistry:
    """Linked Data Proof Suite Registry.

    This registry enables plugging in suite implementations.
    """

    def __init__(self):
        """Initialize registry."""
        self.proof_suites: set[Type[LinkedDataProof]] = set()
        self.issue_suites: set[Type[LinkedDataProof]] = set()
        # assumption, single key type to signature type
        self.proof_key_types_2_signature = {}
        self.issue_key_types_2_signature = {}
    def register_suite(
        self,
        suite: Type[LinkedDataProof],
        proof: bool = False,
    ):
        """Register a new suite."""
        if proof:
            self.proof_suites.add(suite)
        else:
            self.issue_suites.add(suite)

    def register_signature(
        self,
        signature_type,
        key_type: KeyType,
    ):
        """Register a new signature."""
        self.key_types_2_signature[key_type] = signature_type
    
    @property
    def registered(self) -> Set[Type[LinkedDataProof]]:
        """Return set of registered suites."""
        return self.issue_suites | self.proof_suites

    @property
    def signature_type_2_suites(self):
        return {suite.signature_type: suite for suite in self.issue_suites} | {
            suite.signature_type: suite for suite in self.proof_suites
        }

    @property
    def signature_type_2_key_types(self,signature):
        """Returns key types for signature type."""
        for key_type, value in self.key_types_2_signature:
            

    @property
    def signature_types(self):
        """Return all signature types."""
        return self.signature_type_2_suites.keys()

    def is_supported(self, signature_type):
        """Check suite support."""
        return signature_type in self.signature_types

    def get_all_suites(self, wallet: BaseWallet):
        """Get all supported suites for verifying presentation."""
        
        return [
            suite(
                key_pair=WalletKeyPair(wallet=wallet, key_type=key_type),
            )
            for key_type, suite in self.key_types_2_signature.items()
        ]

    # pres_exch_handler
    def _get_verification_method(self, did: str):
        """Get the verification method for a did."""
        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        elif did.startswith("did:sov:"):
            # key-1 is what uniresolver uses for key id
            return f"{did}#key-1"
        else:
            raise CredFormatError(
                f"Unable to get retrieve verification method for did {did}"
            )

    def get_suite(
        self,
        *,
        wallet: BaseWallet,
        issuer_id: str = None,
        did_info: DIDInfo = None,
        signature_type,
        key_type: KeyType = None,
        proof: dict = None,
    ):
        """Get signature suite for signing presentation."""
        verification_method = (
            self._get_verification_method(issuer_id) if issuer_id else ""
        )
        # Get signature class based on proof type
        SignatureClass = self.signature_type_2_suites[signature_type]
        # Generically create signature class
        return SignatureClass(
            verification_method=verification_method,
            proof=proof,
            key_pair=WalletKeyPair(
                wallet=wallet,
                key_type=key_type,
                public_key_base58=did_info.verkey if did_info else None,
            ),
        )
