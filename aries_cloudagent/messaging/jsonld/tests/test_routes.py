import pytest
import unittest
import asyncio
import pytest
from asynctest import mock as async_mock, TestCase as AsyncTestCase
from ....messaging.models.base import BaseModelError
from ....wallet.error import WalletError
from ....config.base import InjectionError
from ....storage.error import StorageError, StorageNotFoundError
import json
from copy import deepcopy
from pyld import jsonld
from .. import credential
from ....admin.request_context import AdminRequestContext
from ....wallet.base import BaseWallet
from .. import routes as test_module
from ....resolver.did_resolver import DIDResolver
from ....resolver.did_resolver_registry import DIDResolverRegistry
from ....resolver.base import DIDNotFound, DIDMethodNotSupported, BaseDIDResolver, ResolverType
from ....resolver.tests import DOC
from ....resolver.default.indy import IndyDIDResolver
from pydid import DIDDocument, VerificationMethod, DID, DIDUrl, VerificationSuite

did_doc = DIDDocument.deserialize(DOC)


@pytest.fixture
def mock_resolver():
    did_resolver = async_mock.MagicMock()
    did_resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
    url = "did:example:1234abcd#4"
    did_resolver.dereference = async_mock.CoroutineMock(
        return_value=did_doc.dereference(url)
    )
    yield did_resolver


@pytest.fixture
def mock_sign_credential():
    temp = test_module.sign_credential
    sign_credential = async_mock.CoroutineMock(return_value="fake_signage")
    test_module.sign_credential = sign_credential
    yield test_module.sign_credential
    test_module.sign_credential = temp


@pytest.fixture
def mock_verify_credential():
    temp = test_module.verify_credential
    verify_credential = async_mock.CoroutineMock(return_value="fake_verify")
    test_module.verify_credential = verify_credential
    yield test_module.verify_credential
    test_module.verify_credential = temp


@pytest.fixture
def mock_sign_request(mock_sign_credential, mock_resolver):
    context = AdminRequestContext.test_context({DIDResolver: mock_resolver})
    outbound_message_router = async_mock.CoroutineMock()
    request_dict = {
        "context": context,
        "outbound_message_router": outbound_message_router,
    }
    request = async_mock.MagicMock(
        match_info={},
        query={},
        json=async_mock.CoroutineMock(
            return_value={
                "verkey": "fake_verkey",
                "doc": {},
                "options": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-10T21:35:35Z",
                    "verificationMethod": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "proofPurpose": "assertionMethod",
                },
            },
        ),
        __getitem__=lambda _, k: request_dict[k],
    )
    yield request


@pytest.fixture
def mock_verify_request(mock_verify_credential, mock_resolver):
    context = AdminRequestContext.test_context({DIDResolver: mock_resolver})
    outbound_message_router = async_mock.CoroutineMock()
    request_dict = {
        "context": context,
        "outbound_message_router": outbound_message_router,
    }
    request = async_mock.MagicMock(
        match_info={},
        query={},
        json=async_mock.CoroutineMock(
            return_value={
                "doc": {
                    "@context": "https://www.w3.org/2018/credentials/v1",
                    "type": "VerifiablePresentation",
                    "holder": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                    "proof": {
                        "type": "Ed25519Signature2018",
                        "created": "2021-02-16T15:21:38.512Z",
                        "challenge": "5103d61a-bd26-4b1a-ab62-87a2a71281d3",
                        "domain": "svip-issuer.ocs-support.com",
                        "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..mH_j_Y7MUIu_KXU_1Dy1BjE4w52INieSPaN7FPtKQKZYTRydPYO5jbjeM-uWB5BXpxS9o-obI5Ztx5IXex-9Aw",
                        "proofPurpose": "authentication",
                        "verificationMethod": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                    },
                }
            }
        ),
        __getitem__=lambda _, k: request_dict[k],
    )
    yield request


@pytest.fixture
def mock_response():
    json_response = async_mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest.mark.asyncio
async def test_sign(mock_sign_request, mock_response):
    await test_module.sign(mock_sign_request)
    mock_response.assert_called_once_with({"signed_doc": "fake_signage"})


@pytest.mark.parametrize(
    "error", [DIDNotFound, DIDMethodNotSupported, WalletError, InjectionError]
)
@pytest.mark.asyncio
async def test_sign_bad_req_error(mock_sign_request, mock_response, error):
    test_module.sign_credential = async_mock.CoroutineMock(side_effect=error())
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.sign(mock_sign_request)


@pytest.mark.asyncio
async def test_sign_bad_ver_meth_deref_req_error(
    mock_resolver, mock_sign_request, mock_response
):
    mock_resolver.dereference.return_value = None
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.sign(mock_sign_request)


@pytest.mark.asyncio
async def test_verify(mock_verify_request, mock_response):
    await test_module.verify(mock_verify_request)
    mock_response.assert_called_once_with({"valid": "fake_verify"})


@pytest.mark.parametrize(
    "error", [DIDNotFound, DIDMethodNotSupported, WalletError, InjectionError]
)
@pytest.mark.asyncio
async def test_verify_bad_req_error(mock_verify_request, mock_response, error):
    test_module.verify_credential = async_mock.CoroutineMock(side_effect=error())
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.verify(mock_verify_request)


@pytest.mark.asyncio
async def test_verify_bad_ver_meth_deref_req_error(
    mock_resolver, mock_verify_request, mock_response
):
    mock_resolver.dereference.return_value = None
    with pytest.raises(test_module.web.HTTPBadRequest):
        await test_module.verify(mock_verify_request)


@pytest.mark.asyncio
async def test_register():
    mock_app = async_mock.MagicMock()
    mock_app.add_routes = async_mock.MagicMock()
    await test_module.register(mock_app)
    mock_app.add_routes.assert_called_once()


def test_post_process_routes():
    mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
    test_module.post_process_routes(mock_app)
    assert "tags" in mock_app._state["swagger_dict"]


class SovResolver(BaseDIDResolver):
    def __init__(self, resolved=None, native: bool = False):
        super().__init__(ResolverType.NATIVE if native else ResolverType.NON_NATIVE)
        self._supported_methods = ["sov"]
        self.resolved = resolved

    async def setup(self, context):
        pass

    @property
    def supported_methods(self):
        return self._supported_methods

    async def _resolve(self, profile, did):
        if isinstance(self.resolved, Exception):
            raise self.resolved
        return self.resolved.serialize()

class TestJSONLDRoutes(AsyncTestCase):
    async def setUp(self):
        self.context = AdminRequestContext.test_context()
        self.ledger = async_mock.MagicMock()
        self.registery = DIDResolverRegistry()
        self.registery.register(IndyDIDResolver())
        self.resolver = DIDResolver(self.registery)
        self.context.injector.bind_instance(DIDResolver, self.resolver)
        self.did_info = await (await self.context.session()).wallet.create_local_did()
        self.res_ver_meth = VerificationMethod(
			id_= DIDUrl("did:sov:5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF#key-2"),
			suite =VerificationSuite(type_ = "Ed25519Verification2018",verification_material_prop="5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF"),
			controller= DID("did:sov:5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF"),
			material= "5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF"
        )
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_verify_credential(self):
        POSTED_REQUEST = {  # posted json
            "verificationMethod": (
                # pulled from the did:key in example
                "did:sov:5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF#key-2"
            ),
            "doc": {
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                "id": "http://example.gov/credentials/3732",
                "type": ["VerifiableCredential", "UniversityDegreeCredential"],
                "issuer": ("did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
                "issuanceDate": "2020-03-10T04:24:12.164Z",
                "credentialSubject": {
                    "id": (
                        "did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "degree": {
                        "type": "BachelorDegree",
                        "name": "Bachelor of Science and Arts",
                    },
                },
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-10T21:35:35Z",
                    "verificationMethod": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc"
                        "4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZD"
                        "VzrJzFrwahc4tXLt9DoHd"
                    ),
                    "proofPurpose": "assertionMethod",
                    "jws": (
                        "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaX"
                        "QiOlsiYjY0Il19..l9d0YHjcFAH2H4dB9xlWFZQLUp"
                        "ixVCWJk0eOt4CXQe1NXKWZwmhmn9OQp6YxX0a2Lffe"
                        "gtYESTCJEoGVXLqWAA"
                    ),
                },
            },
        }

        self.request.json = async_mock.CoroutineMock(return_value=POSTED_REQUEST)
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.verify(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"valid": True})  # expected response

        # compact, expand take a LONG TIME: do them once above, mock for error cases
        with async_mock.patch.object(
            jsonld, "compact", async_mock.MagicMock()
        ) as mock_compact, async_mock.patch.object(
            jsonld, "expand", async_mock.MagicMock()
        ) as mock_expand, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_expand.return_value = [async_mock.MagicMock()]
            mock_compact.return_value = {
                "@context": "...",
                "id": "...",
                "type": ["...", "..."],
                "proof": {},
                "https://www.w3.org/2018/credentials#credentialSubject": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                    "https://example.org/examples#degree": {
                        "type": "https://example.org/examples#BachelorDegree",
                        "http://schema.org/name": {
                            "type": "http://www.w3.org/1999/02/22-rdf-syntax-ns#HTML",
                            "@value": "Bachelor of Science and Arts",
                        },
                    },
                },
                "https://www.w3.org/2018/credentials#issuanceDate": {
                    "type": "xsd:dateTime",
                    "@value": "2020-03-10T04:24:12.164Z",
                },
                "https://www.w3.org/2018/credentials#issuer": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                },
            }
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.verify(self.request)
            assert "error" in json.loads(result)

        print("\n>> START X-ATTR-CRED-SUBJECT")
        with async_mock.patch.object(
            jsonld, "compact", async_mock.MagicMock()
        ) as mock_compact, async_mock.patch.object(
            jsonld, "expand", async_mock.MagicMock()
        ) as mock_expand, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_expand.return_value = [async_mock.MagicMock()]
            mock_compact.return_value = {
                "@context": "...",
                "id": "...",
                "type": ["...", "..."],
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-10T21:35:35Z",
                    "jws": (
                        "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19"
                        ".."
                        "l9d0YHjcFAH2H4dB9xlWFZQLUpixVCWJk0eOt4CXQe1NXKWZwmhmn9OQ"
                        "p6YxX0a2LffegtYESTCJEoGVXLqWAA"
                    ),
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": (
                        "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                },
                "https://www.w3.org/2018/credentials#credentialSubject": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                },
                "https://www.w3.org/2018/credentials#issuanceDate": {
                    "type": "xsd:dateTime",
                    "@value": "2020-03-10T04:24:12.164Z",
                },
                "https://www.w3.org/2018/credentials#issuer": {
                    "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                },
            }
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.verify(self.request)
            assert "error" in json.loads(result)

        self.context.session_inject[BaseWallet] = None
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.verify(self.request)

    async def test_sign_credential(self):
        POSTED_REQUEST = {  # posted json
            "verificationMethod": self.did_info.verkey,
            "doc": {
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1",
                    ],
                    "id": "http://example.gov/credentials/3732",
                    "type": [
                        "VerifiableCredential",
                        "UniversityDegreeCredential",
                    ],
                    "issuer": (
                        "did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "issuanceDate": "2020-03-10T04:24:12.164Z",
                    "credentialSubject": {
                        "id": (
                            "did:key:"
                            "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                        ),
                        "degree": {
                            "type": "BachelorDegree",
                            "name": u"Bachelor of Encyclopædic Arts",
                        },
                    },
                },
                "options": {
                    # "type": "Ed25519Signature2018",  exercise default
                    # "created": exercise default of now
                    "creator": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "verificationMethod": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "proofPurpose": "assertionMethod",
                },
            },
        }
        self.request.json = async_mock.CoroutineMock(return_value=POSTED_REQUEST)
        self.ledger.resolve.return_value.set_result({
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1",
                    ],
                    "id": "http://example.gov/credentials/3732",
                    "type": [
                        "VerifiableCredential",
                        "UniversityDegreeCredential",
                    ],
                    "issuer": (
                        "did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "issuanceDate": "2020-03-10T04:24:12.164Z",
                    "credentialSubject": {
                        "id": (
                            "did:key:"
                            "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                        ),
                        "degree": {
                            "type": "BachelorDegree",
                            "name": u"Bachelor of Encyclopædic Arts",
                        },
                    },
                },
                "options": {
                    # "type": "Ed25519Signature2018",  exercise default
                    # "created": exercise default of now
                    "creator": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "verificationMethod": (
                        "did:key:"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#"
                        "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
                    ),
                    "proofPurpose": "assertionMethod",
            },
        })
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.sign(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once()
            assert "signed_doc" in mock_response.call_args[0][0]
            assert "error" not in mock_response.call_args[0][0]

        # short circuit: does not reach expand/compact
        posted_request_x = deepcopy(POSTED_REQUEST)
        posted_request_x["doc"]["options"].pop("verificationMethod")
        posted_request_x["doc"]["options"].pop("creator")
        self.request.json = async_mock.CoroutineMock(return_value=posted_request_x)
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.sign(self.request)
            assert "error" in json.loads(result)

        # compact, expand take a LONG TIME: do them once above, mock for error cases
        posted_request = deepcopy(POSTED_REQUEST)
        self.request.json = async_mock.CoroutineMock(return_value=posted_request)
        with async_mock.patch.object(
            jsonld, "compact", async_mock.MagicMock()
        ) as mock_compact, async_mock.patch.object(
            jsonld, "expand", async_mock.MagicMock()
        ) as mock_expand, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_expand.return_value = [async_mock.MagicMock()]
            mock_compact.return_value = {}  # drop all attributes
            mock_response.side_effect = lambda x: json.dumps(x)
            result = await test_module.sign(self.request)
            assert "error" in json.loads(result)

        self.context.session_inject[BaseWallet] = None
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.sign(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()
