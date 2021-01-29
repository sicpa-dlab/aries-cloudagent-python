from marshmallow import Schema, fields, post_load


class ServiceSchema(Schema):
    """
    Example
    {"id": "1",
     "type": "one",
     "priority": 1,

     "recipientKeys": [
         "~XXXXXXXXXXXXXXXX",
         "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"],
     "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
     "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2"}
    """
    id = fields.Str()
    type = fields.Str()
    priority = fields.Int()
    recipientKeys = fields.List(fields.Str())
    routingKeys = fields.List(fields.Str())
    serviceEndpoint = fields.Str()

    @post_load
    def make_service(self, data, **kwargs):
        from ..service import Service
        return Service(**data)


