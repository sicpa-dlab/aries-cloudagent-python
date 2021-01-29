from marshmallow import Schema, fields
from .publickeyschema import PublicKeySchema
from .serviceschema import ServiceSchema
from .authenticationschema import AuthenticationSchema
from .verificationmethodschema import VerificationMethodSchema

class DIDDocSchema(Schema):

    id = fields.Str()
    publicKey = fields.List(fields.Nested(PublicKeySchema))
    authentication = fields.List(fields.Nested(AuthenticationSchema))
    service = fields.List(fields.Nested(ServiceSchema))
    verificationMethod = fields.Nested(VerificationMethodSchema)

