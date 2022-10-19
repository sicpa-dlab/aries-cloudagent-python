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
        self.suites_proof: set[Type[LinkedDataProof]] = set()
        self.suites_issue: set[Type[LinkedDataProof]] = {Ed25519Signature2018}
        # We only want to add bbs suites to supported if the module is installed
        if BbsBlsSignature2020.BBS_SUPPORTED:
            self.suites_issue.add(BbsBlsSignature2020)
            self.suites_proof.add(BbsBlsSignatureProof2020)

    def register(
        self,
        suite: Type[LinkedDataProof],
        proof: bool = False,
    ):
        """Register a new suite."""
        if proof:
            self.suites_proof.add(suite)
        else:
            self.suites_issue.add(suite)

    @property
    def registered(self) -> Set[Type[LinkedDataProof]]:
        """Return set of registered suites."""
        return self.suites_issue | self.suites_proof

    @property
    def signature_type_2_suites(self):
        return {suite.signature_type: suite for suite in self.suites_issue} | {
            suite.signature_type: suite for suite in self.suites_proof
        }

    @property
    def signature_types(self):
        """Return all signature types."""
        return self.signature_type_2_suites.keys()

    def is_supported(self, signature_type):
        """Check suite support."""
        return signature_type in self.signature_types

    '''def get_all_suites(self, wallet: BaseWallet):
        """Get all supported suites for verifying presentation."""
        return [
            suite(
                key_pair=WalletKeyPair(wallet=wallet, key_type=key_type),
            )
            for key_type, suite in self.proof_type_to_suite.items()
        ]'''

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
