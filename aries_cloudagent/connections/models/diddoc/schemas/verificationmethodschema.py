from marshmallow import Schema, fields


class VerificationMethodSchema(Schema):
    """

    Example
    {"type": "Ed25519VerificationKey2018",
     "id": "did:sov:CYQLsccvwhMTowprMjGjQ6#key-1",
     "publicKeyBase58": "CLFRfp2wa3ifbsVvdq52WcpEy7aujactsoqQgxkz7ZKR"}
    """
    id = fields.Str()
    type = fields.Str()
    publicKeyBase58 = fields.Str()

