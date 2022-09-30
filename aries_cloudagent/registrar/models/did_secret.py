from ...messaging.models.base import BaseModel, BaseModelSchema

class BaseMethod:
    """."""
class VerificationMethod(BaseMethod):
    """."""
class DIDSecret(BaseModel):
    class Meta:
    """."""

    schema_class = "DIDSecretSchema"

    def __init__(self, did, options, method):
        super().__init__()
        self._did = did
        self._options = options
        self._verification_methods = [method]
        self._secrets = {"verification_method": method}
    

        
class DIDSecretSchema(BaseModelSchema):
    """."""
    