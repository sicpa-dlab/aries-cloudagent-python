from ....wallet.key_type import BLS12381G2, ED25519
from .bbs_bls_signature_2020 import BbsBlsSignature2020
from .bbs_bls_signature_proof_2020 import BbsBlsSignatureProof2020
from .ed25519_signature_2018 import Ed25519Signature2018
from .registry import LDProofSuiteRegistry


def default_registry() -> LDProofSuiteRegistry:
    """Return the default registry."""
    registry = LDProofSuiteRegistry()
    registry.register(
        Ed25519Signature2018, Ed25519Signature2018.signature_type, [ED25519]
    )
    if BbsBlsSignature2020.BBS_SUPPORTED:
        registry.register(
            BbsBlsSignature2020, BbsBlsSignature2020.signature_type, [BLS12381G2]
        )
        registry.register(
            BbsBlsSignatureProof2020,
            BbsBlsSignatureProof2020.signature_type,
            [BLS12381G2],
            derivable=True,
        )
    return registry
