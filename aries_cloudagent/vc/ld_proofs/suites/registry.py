"""Signature Suite Registry."""


from typing import Dict, Sequence, Set, Type

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
        self.proof_type_to_suite: Dict[str, Type[LinkedDataProof]] = {}
        self.derived_proof_type_to_suite: Dict[str, Type[LinkedDataProof]] = {}

    def register(
        self,
        suite: Type[LinkedDataProof],
        signature_type: str,
        key_types: Sequence[KeyType],
        derivable: bool = False,
    ):
        """Register a new suite."""
        self.proof_type_to_suite[signature_type] = suite

        for key_type in key_types:
            self.key_type_to_suite[key_type] = suite

        if derivable:
            self.derived_proof_type_to_suite[signature_type] = suite

    @property
    def registered(self) -> Set[Type[LinkedDataProof]]:
        """Return set of registered suites."""
        return set(self.proof_type_to_suite.values())

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
