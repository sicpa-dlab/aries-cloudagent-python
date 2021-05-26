from jwcrypto import jwk, jws, jwt
from ...wallet.base import BaseWallet
from ...wallet.util import b64_to_bytes, b64_to_str, bytes_to_b64, str_to_b64
from .credential import b64encode, b64decode ,jws_sign as _jws_sign
import json


# TODO: should we restrict alowed algs? jws.default_allowed_algs = []
async def jws_deserialize(doc: str):
    jws_token = jws.JWS(json.dumps(doc))
    return jws_token.deserialize(jws_token)


async def jws_serialize(doc: str):
    jws_token = jws.JWS(json.dumps(doc))
    return jws_token.serialize()


async def jws_sign(session, doc: str, verkey: str):
    return _jws_sign(session, doc, verkey)


async def jws_verify(session, doc, signature, public_key):
    jws_token = jws.JWS(json.dumps(doc))
    return jws_token.verify().get('valid', False)


async def jwt_deserialize(doc: str):
    jwt_token = jwt.JWT(json.dumps(doc))
    return jwt_token.deserialize()


async def jwt_serialize(doc: str):
    jwt_token = jwt.JWT(json.dumps(doc))
    return jwt_token.serialize()


def prepare_claims(claims):
    # TODO: do something to validate the claims structure..
    return claims


async def jwt_sign(session, payload, verkey):
    header = b64encode(
        {
            "typ": "JWT",
            "alg": "EdDSA",
            "b64": False,
            "crit": ["b64"]
        }
    )
    claims = b64encode(prepare_claims(payload))
    parts_to_sign = header + "." + claims
    wallet = session.inject(BaseWallet, required=True)
    signature = await wallet.sign_message(parts_to_sign, verkey)
    encoded_signature = bytes_to_b64(signature, urlsafe=True, pad=False)
    return parts_to_sign + "." + encoded_signature


async def jwt_verify(jwt_token):
    jwt_token = jwt.JWT(json.dumps(jwt_token))
    return jwt_token.verify().get('valid', False)
