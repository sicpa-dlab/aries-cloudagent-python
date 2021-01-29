from marshmallow import Schema, fields


class AuthenticationSchema(Schema):
    """
    Example:
     {"id": "LjgpST2rjsoxYegQDRm7EL#keys-1",
     "type": "Ed25519VerificationKey2018",
     "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
     "publicKeyBase58": "~XXXXXXXXXXXXXXXX",
     "verificationMethod": "did:sov:WRfXPg8dantKVubE3HX8pw#key-1"
     "publicKey": "did:sov:LjgpST2rjsoxYegQDRm7EL#4",
     "publicKeyPem": "-----BEGIN PUBLIC A..."}

    """
    id = fields.Str()
    type = fields.Str()
    controller = fields.Str()
    publicKeyBase58 = fields.Str()
    verificationMethod = fields.Str()
    publicKey = fields.Str()
    publicKeyPem = fields.Str()

