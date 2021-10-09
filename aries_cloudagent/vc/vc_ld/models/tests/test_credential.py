from datetime import datetime, timezone
from unittest import TestCase

from marshmallow.utils import INCLUDE

from ...models.credential import VerifiableCredential
from ...models.linked_data_proof import LDProof
from ....ld_proofs.constants import (
    CREDENTIALS_CONTEXT_V1_URL,
    VERIFIABLE_CREDENTIAL_TYPE,
)

CREDENTIAL = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/citizenship/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
    "type": ["VerifiableCredential", "PermanentResidentCard"],
    "issuer": "did:example:489398593",
    "identifier": "83627465",
    "name": "Permanent Resident Card",
    "description": "Government of Example Permanent Resident Card.",
    "issuanceDate": "2019-12-03T12:19:52Z",
    "expirationDate": "2029-12-03T12:19:52Z",
    "credentialSubject": {
        "id": "did:example:b34ca6cd37bbf23",
        "type": ["PermanentResident", "Person"],
        "givenName": "JOHN",
        "familyName": "SMITH",
        "gender": "Male",
        "image": "data:image/png;base64,iVBORw0KGgokJggg==",
        "residentSince": "2015-01-01",
        "lprCategory": "C09",
        "lprNumber": "999-999-999",
        "commuterClassification": "C1",
        "birthCountry": "Bahamas",
        "birthDate": "1958-07-17",
    },
}


VC_PROOF0 = {
    "type": "BbsBlsSignatureProof2020",
    "created": "2020-12-14T03:11:30Z",
    "nonce": "CF69iO3nfvqRsRBNElE8b4wO39SyJHPM7Gg1nExltW5vSfQA1lvDCR/zXX1To0/4NLo=",
    "proofPurpose": "assertionMethod",
    "proofValue": "AA0f/7dHROgM2jXZiK0UmY5956/26qbbWF1sKgTMLx1NWEJqrE2ptwlREsxxrqZDRy5pxIFeSxDe08yWxDIk7zefzbwHd04hfbs0oaE2e9TMxIhfUZnct5Br7XenOwpZkkW1d7nt/yUFclgLCAIg+8B3UDpsuzv4rAJ3bTvD69nrMJPwC+Ao7meBgPcAaubNirSqrgAAAHSqzxvoLIRtX8mcq90yIHHuAcThiP63ChKE9c49pJboQ5FBA1aiMIIAJ+J7JPZtBGUAAAACIly7gNiA2nXJAVTKNepEQOtdyEU1gqExcaxWhMgX6nBCRGCwypy5lDDj2XWsvcuzPcvrpvaBxIBvTBAVjKDODaExOe1FKwA2t6F80wvt1BrEQpa5mG9YsI7Hw0wwl+c0SekC/WYlVW0oFjdICH+ZsAAAAAJlYX1Br69N/IAemIkmBvU/7bcIGssDcGL4hNzuTe0a8FnXYhUHyYmnMYFgZMv2ht2nMZiSwAugP2y3dFAU99bU",
    "verificationMethod": "did:example:489398593#test",
}

VC_PROOF1 = {
    "type": "BbsBlsSignature2020",
    "proofPurpose": "assertionMethod",
    "verificationMethod": "did:key:zUC7Jc1v55hbeejGm5JGQvzne1t8BK6CpoDRPdhhrMCDrVKouN1DQxgN7mgqW3sL3JYqxZRFCZKdJLyj5Sd2YjRRg1dFdMYZdd3pJjy3WPdjUGbtRaU83YFfDqq8cJqkazYpeA4#zUC7Jc1v55hbeejGm5JGQvzne1t8BK6CpoDRPdhhrMCDrVKouN1DQxgN7mgqW3sL3JYqxZRFCZKdJLyj5Sd2YjRRg1dFdMYZdd3pJjy3WPdjUGbtRaU83YFfDqq8cJqkazYpeA4",
    "created": "2021-10-05T15:05:20.179917",
    "proofValue": "h4oJQY3dZvBv11d/HS8XzIdR76QbPQ0s64rJDC16t1yxTMxZF08GoPx1AoSCHHvsI4wMJ2VTtGZ6nb+//Sj2lwcAxsJJyYx7uqGI5GGmb0sLkw/tAszBPk0ffUb2pXkgQ1x/e3Gev40JD5739l8Nxg==",
}

VERIFIABLE_CREDENTIAL = {**CREDENTIAL, "proof": VC_PROOF0}


class TestLinkedDataProof(TestCase):
    """LinkedDataProof tests"""

    def test_serde(self):
        """Test de/serialization."""
        proof = LDProof.deserialize(VC_PROOF0)
        assert type(proof) == LDProof

        proof_dict = proof.serialize()
        assert proof_dict == VC_PROOF0

    def test_set_operations(self):
        proof0 = LDProof.deserialize(VC_PROOF0)
        proof1 = LDProof.deserialize(VC_PROOF1)
        copy_proof0 = LDProof.deserialize(VC_PROOF0)
        copy_proof1 = LDProof.deserialize(VC_PROOF1)
        assert {proof0, proof1} - {proof1} == {proof0}
        assert {proof0, proof1} - {copy_proof1} == {proof0}


class TestVerifiableCredential(TestCase):
    """VerifiableCredential tests"""

    def test_serde_credential(self):
        """Test de/serialization."""
        credential = VerifiableCredential.deserialize(CREDENTIAL, unknown=INCLUDE)
        assert type(credential) == VerifiableCredential

        credential_dict = credential.serialize()
        assert credential_dict == CREDENTIAL

    def test_serde_verifiable_credential(self):
        """Test de/serialization."""
        credential = VerifiableCredential.deserialize(
            VERIFIABLE_CREDENTIAL, unknown=INCLUDE
        )
        assert type(credential) == VerifiableCredential

        credential_dict = credential.serialize()
        assert credential_dict == VERIFIABLE_CREDENTIAL

    def test_properties(self):
        credential = VerifiableCredential()

        credential.context = [CREDENTIALS_CONTEXT_V1_URL]
        assert credential.context == [CREDENTIALS_CONTEXT_V1_URL]

        credential.add_context("https://some.context")
        credential.add_context({"some": "context"})
        assert credential.context == [
            CREDENTIALS_CONTEXT_V1_URL,
            "https://some.context",
            {"some": "context"},
        ]

        assert credential.context_urls == [
            CREDENTIALS_CONTEXT_V1_URL,
            "https://some.context",
        ]

        with self.assertRaises(Exception):
            credential.context = ["IsNotVCContext"]

        credential.type = [VERIFIABLE_CREDENTIAL_TYPE]
        assert credential.type == [VERIFIABLE_CREDENTIAL_TYPE]

        credential.add_type("Sometype")
        assert credential.type == [VERIFIABLE_CREDENTIAL_TYPE, "Sometype"]

        with self.assertRaises(Exception):
            credential.type = ["DoesNotIncludeCredentialType"]

        credential.id = "http://someid.com"
        assert credential.id == "http://someid.com"

        credential.id = None
        assert not credential.id

        with self.assertRaises(Exception):
            credential.id = "not-an-uri"

        assert not credential.issuer_id
        credential.issuer_id = "http://some_id.com"
        assert credential.issuer_id == "http://some_id.com"

        assert credential.issuer == "http://some_id.com"
        credential.issuer = {"id": "http://some_id.com"}
        assert credential.issuer == {"id": "http://some_id.com"}
        assert credential.issuer_id == "http://some_id.com"
        credential.issuer_id = "http://some-other-id"
        assert credential.issuer == {"id": "http://some-other-id"}

        with self.assertRaises(Exception):
            credential.issuer = {"id": "not-an-uri"}

        with self.assertRaises(Exception):
            credential.issuer = "not-an-uri"

        with self.assertRaises(Exception):
            credential.issuer_id = "not-an-uri"

        with self.assertRaises(Exception):
            credential.issuer = {"not-id": "not-id"}

        date = datetime.now(timezone.utc)
        credential.issuance_date = date
        assert credential.issuance_date == date.isoformat()
        credential.issuance_date = date.isoformat()
        assert credential.issuance_date == date.isoformat()
        date = datetime(2019, 12, 11, 3, 50, 55, 0)
        credential.issuance_date = date
        assert (
            credential.issuance_date
            == datetime(2019, 12, 11, 3, 50, 55, 0, timezone.utc).isoformat()
        )

        date = datetime.now(timezone.utc)
        credential.expiration_date = date
        assert credential.expiration_date == date.isoformat()
        credential.expiration_date = date.isoformat()
        assert credential.expiration_date == date.isoformat()
        date = datetime(2019, 12, 11, 3, 50, 55, 0)
        credential.expiration_date = date
        assert (
            credential.expiration_date
            == datetime(2019, 12, 11, 3, 50, 55, 0, timezone.utc).isoformat()
        )

        assert not credential.credential_subject
        assert not credential.credential_subject_ids
        credential.credential_subject = {"some": "props"}
        assert credential.credential_subject == {"some": "props"}
        assert credential.credential_subject_ids == []
        credential.credential_subject = [{"some": "props"}]
        assert credential.credential_subject == [{"some": "props"}]
        assert credential.credential_subject_ids == []

        credential.credential_subject = {"id": "some:uri"}
        assert credential.credential_subject_ids == ["some:uri"]

        assert credential == credential
        assert credential != 10

    def test_verifiable_credential_proof_single_or_multiple(self):
        credential = VerifiableCredential.deserialize(
            VERIFIABLE_CREDENTIAL, unknown=INCLUDE
        )
        assert isinstance(credential, VerifiableCredential)
        assert credential.proof
        assert credential.proof[0].serialize() == VC_PROOF0
        assert credential.serialize() == VERIFIABLE_CREDENTIAL
        credential = VerifiableCredential.deserialize(
            {**CREDENTIAL, "proof": [VC_PROOF0]}, unknown=INCLUDE
        )
        assert isinstance(credential, VerifiableCredential)
        assert credential.proof
        assert credential.proof[0].serialize() == VC_PROOF0
        # No way to detect that input was list and preserve so this will
        # always output a singular proof object
        assert credential.serialize() == {**CREDENTIAL, "proof": VC_PROOF0}
        credential = VerifiableCredential.deserialize(
            {**CREDENTIAL, "proof": [VC_PROOF0, VC_PROOF1]}, unknown=INCLUDE
        )
        assert isinstance(credential, VerifiableCredential)
        assert credential.proof
        assert credential.proof[0].serialize() == VC_PROOF0
        assert credential.proof[1].serialize() == VC_PROOF1
        assert credential.serialize() == {**CREDENTIAL, "proof": [VC_PROOF0, VC_PROOF1]}
