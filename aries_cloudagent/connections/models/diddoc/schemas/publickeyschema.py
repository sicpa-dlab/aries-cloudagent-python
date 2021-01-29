from marshmallow import Schema, fields, post_load


class PublicKeySchema(Schema):
    """

    {"id": "3",
     "type": "RsaVerificationKey2018",
     "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
     "publicKeyPem": "-----BEGIN PUBLIC X...",
     "usage": "signing",
     "publicKeyBase58",
     "publicKeyHex": "0361f286ada2a6b2c74bc6ed44a71ef59fb9dd15eca9283cbe5608aeb516730f33",
     "publicKeyJwk": {
        "kty": "EC",
        "crv": "secp256k1",
        "kid": "JUvpllMEYUZ2joO59UNui_XYDqxVqiFLLAJ8klWuPBw",
        "x": "dWCvM4fTdeM0KmloF57zxtBPXTOythHPMm1HCLrdd3A",
        "y": "36uMVGM7hnw-N6GnjFcihWE3SkrhMLzzLCdPMXPEXlA"},

      }
    """
    id = fields.Str()
    usage = fields.Str()
    controller = fields.Str()
    type = fields.Str()

    publicKeyHex = fields.Str()
    publicKeyPem = fields.Str()
    publicKeyJwk = fields.Dict()
    publicKeyBase58 = fields.Str()

    @post_load
    def make_service(self, data, **kwargs):
        from ..publickey import PublicKey
        return PublicKey(**data)
