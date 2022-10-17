"""Signature Suite Registry."""


from typing import Dict, Sequence, Set
from vc.ld_proofs.crypto.wallet_key_pair import WalletKeyPair
from wallet.did_info import DIDInfo
from ....vc.ld_proofs import (
    Ed25519Signature2018,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
    WalletKeyPair,
    DocumentLoader,
)
from ....vc.ld_proofs.constants import (
    SECURITY_CONTEXT_BBS_URL,
    EXPANDED_TYPE_CREDENTIALS_CONTEXT_V1_VC_TYPE,
)
from wallet.base import BaseWallet

from ....wallet.key_type import KeyType
from .linked_data_proof import LinkedDataProof


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
        self.key_type_to_suite: Dict[KeyType, LinkedDataProof] = {}
        self.proof_type_to_suite: Dict[str, LinkedDataProof] = {}
        self.derived_proof_type_to_suite: Dict[str, LinkedDataProof] = {}
        # pres_exch_handler
        self.ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
            Ed25519Signature2018: KeyType.ED25519,
        }

        if BbsBlsSignature2020.BBS_SUPPORTED:
            self.ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[BbsBlsSignature2020] = KeyType.BLS12381G2

        self.DERIVE_SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
            BbsBlsSignatureProof2020: KeyType.BLS12381G2,
        }
        self.PROOF_TYPE_SIGNATURE_SUITE_MAPPING = {
            suite.signature_type: suite
            for suite, key_type in self.ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
        }
        self.DERIVED_PROOF_TYPE_SIGNATURE_SUITE_MAPPING = {
            suite.signature_type: suite
            for suite, key_type in self.DERIVE_SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
        }
        # handler
        self.SUPPORTED_ISSUANCE_SUITES = {Ed25519Signature2018}
        self.SIGNATURE_SUITE_KEY_TYPE_MAPPING = {Ed25519Signature2018: KeyType.ED25519}


        # We only want to add bbs suites to supported if the module is installed
        if BbsBlsSignature2020.BBS_SUPPORTED:
            self.SUPPORTED_ISSUANCE_SUITES.add(BbsBlsSignature2020)
            self.SIGNATURE_SUITE_KEY_TYPE_MAPPING[BbsBlsSignature2020] = KeyType.BLS12381G2


        self.PROOF_TYPE_SIGNATURE_SUITE_MAPPING = {
            suite.signature_type: suite
            for suite, key_type in self.SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
        }

        self.KEY_TYPE_SIGNATURE_SUITE_MAPPING = {
            key_type: suite for suite, key_type in self.SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
        }

    def register(
        self,
        suite: LinkedDataProof,
        key_types: Sequence[KeyType],
        derivable: bool = False,
    ):
        """Register a new suite."""
        self.proof_type_to_suite[suite.signature_type] = suite

        for key_type in key_types:
            self.key_type_to_suite[key_type] = suite

        if derivable:
            self.derived_proof_type_to_suite[suite.signature_type] = suite

    @property
    def registered(self) -> Set[LinkedDataProof]:
        """Return set of registered suites."""
        return set(self.proof_type_to_suite.values())

    def from_proof_type(self, proof_type: str) -> LinkedDataProof:
        """Return suite by key type."""
        try:
            return self.proof_type_to_suite[proof_type]
        except KeyError as exc:
            raise UnsupportedProofType(
                f"Proof type {proof_type} is not supported by currently "
                "registered LD Proof suites."
            ) from exc

    def from_derived_proof_type(self, proof_type: str) -> LinkedDataProof:
        """Return derived proof type."""
        try:
            return self.derived_proof_type_to_suite[proof_type]
        except KeyError as exc:
            raise UnsupportedProofType(
                f"Proof type {proof_type} is not supported by currently "
                "registered LD Proof suites."
            ) from exc

    def from_key_type(self, key_type: KeyType) -> LinkedDataProof:
        """Return suite by key type."""
        try:
            return self.key_type_to_suite[key_type]
        except KeyError as exc:
            raise UnsupportedProofType(
                f"Key type {key_type} is not supported by currently "
                "registered LD Proof suites."
            ) from exc

    def is_supported(self, proof_type, key_type):
        """Check suite support."""
        return (
            key_type in self.key_type_to_suite.keys()
            and proof_type in self.proof_type_to_suite.keys()
        )

    async def get_all_suites(self, wallet: BaseWallet):
        """Get all supported suites for verifying presentation."""
        return [
            suite(
                key_pair=WalletKeyPair(wallet=wallet, key_type=key_type),
            )
            for key_type, suite in self.proof_type_to_suite.items()
        ]
        
    # pres_exch_handler
    async def _get_issue_suite(
        self,
        *,
        wallet: BaseWallet,
        issuer_id: str,
    ):
        """Get signature suite for signing presentation."""
        did_info = await self._did_info_for_did(issuer_id)
        verification_method = self._get_verification_method(issuer_id)

        # Get signature class based on proof type
        SignatureClass = self.PROOF_TYPE_SIGNATURE_SUITE_MAPPING[self.proof_type]

        # Generically create signature class
        return SignatureClass(
            verification_method=verification_method,
            key_pair=WalletKeyPair(
                wallet=wallet,
                key_type=self.ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[SignatureClass],
                public_key_base58=did_info.verkey if did_info else None,
            ),
        )

    async def _get_derive_suite(
        self,
        *,
        wallet: BaseWallet,
    ):
        """Get signature suite for deriving credentials."""
        # Get signature class based on proof type
        SignatureClass = self.DERIVED_PROOF_TYPE_SIGNATURE_SUITE_MAPPING[
            "BbsBlsSignatureProof2020"
        ]

        # Generically create signature class
        return SignatureClass(
            key_pair=WalletKeyPair(
                wallet=wallet,
                key_type=self.DERIVE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[SignatureClass],
            ),
        )
    async def _get_suite(
            self,
            *,
            proof_type: str,
            verification_method: str = None,
            proof: dict = None,
            did_info: DIDInfo = None,
        ):
            """Get signature suite for issuance of verification."""
            session = await self.profile.session()
            wallet = session.inject(BaseWallet)

            # Get signature class based on proof type
            SignatureClass = self.PROOF_TYPE_SIGNATURE_SUITE_MAPPING[proof_type]

            # Generically create signature class
            return SignatureClass(
                verification_method=verification_method,
                proof=proof,
                key_pair=WalletKeyPair(
                    wallet=wallet,
                    key_type=self.SIGNATURE_SUITE_KEY_TYPE_MAPPING[SignatureClass],
                    public_key_base58=did_info.verkey if did_info else None,
                ),
            )