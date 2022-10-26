"""Signature Suite Registry."""


from typing import Dict, Set, Type
from aries_cloudagent.did.did_key import DIDKey

from aries_cloudagent.wallet.key_type import KeyType
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
        self.key_type_to_suite: Dict[KeyType, Type[LinkedDataProof]] = {}
        self.suite_to_key_type: Dict[Type[LinkedDataProof], KeyType] = {}
        self.proof_type_to_suite: Dict[str, Type[LinkedDataProof]] = {}
        self.derived_proof_type_to_suite: Dict[str, Type[LinkedDataProof]] = {}

    def register(
        self,
        suite: Type[LinkedDataProof],
        signature_type: str,
        key_type: KeyType,
        derivable: bool = False,
    ):
        """Register a new suite."""
        if derivable:
            self.derived_proof_type_to_suite[signature_type] = suite
            return

        self.proof_type_to_suite[signature_type] = suite

        # TODO KeyType -> Suite is only one-to-one when not including derivable
        # proof types like BbsBlsSignatureProof2020.
        self.key_type_to_suite[key_type] = suite
        self.suite_to_key_type[suite] = key_type

    @property
    def registered(self) -> Set[str]:
        """Return set of registered suites."""
        return set(self.proof_type_to_suite.keys())

    @property
    def registered_types(self) -> Set[Type[LinkedDataProof]]:
        """Return set of registered suites."""
        return set(self.proof_type_to_suite.values())

    def key_type_from_suite(self, suite: Type[LinkedDataProof]) -> KeyType:
        """Return the key type associated with a suite."""
        try:
            return self.suite_to_key_type[suite]
        except KeyError as err:
            raise LDProofSuiteRegistryError(
                f"No key type registered for signature suite {suite}"
            ) from err

    def from_proof_type(self, proof_type: str) -> Type[LinkedDataProof]:
        """Return suite by key type."""
        try:
            return self.proof_type_to_suite[proof_type]
        except KeyError:
            raise UnsupportedProofType(
                f"Proof type {proof_type} is not supported by currently "
                "registered LD Proof suites."
            )

    def from_derived_proof_type(self, proof_type: str) -> Type[LinkedDataProof]:
        """Return derived proof type."""
        try:
            return self.derived_proof_type_to_suite[proof_type]
        except KeyError:
            raise UnsupportedProofType(
                f"Proof type {proof_type} is not supported by currently "
                "registered LD Proof suites."
            )

    def from_key_type(self, key_type: KeyType) -> Type[LinkedDataProof]:
        """Return suite by key type."""
        try:
            return self.key_type_to_suite[key_type]
        except KeyError:
            raise UnsupportedProofType(
                f"Key type {key_type} is not supported by currently "
                "registered LD Proof suites."
            )

    def get_verification_method(self, did: str) -> str:
        """Get the verification method for a did."""

        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        elif did.startswith("did:sov:"):
            # key-1 is what the resolver uses for key id
            return did + "#key-1"
        else:
            # TODO Actually resolve the doc and give the first assertion method
            # This is a hack but it's a similar assumption to what is above.
            return did + "#key-1"
