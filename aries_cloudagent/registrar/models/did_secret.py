from ...messaging.models.base import BaseModel, BaseModelSchema

from marshmallow import INCLUDE, EXCLUDE, Schema, fields


class BaseMethod:
    """Did secret base methods."""

    def __init__(self, id, type, controller, purpose) -> None:
        self._id = id
        self._type = type
        self._controller = controller
        self._purpose = purpose

    @property
    def id(self):
        """The id property.
        - OPTIONAL
        If present, value MUST match the id property of the
            corresponding verification method in DID document.
        If absent, verification method does not correspond
            to any verification method in the DID document."""
        return self._id

    @property
    def type(self):
        """Get did method type.
        - OPTIONAL"""
        return self._type

    @property
    def controller(self):
        """Get did controller.
        - OPTiONAL
        """
        return self._controller

    @property
    def purpose(self):
        """Purpose property.
        JSON array that contains verification relationships such
        as authentication or assertionMethod.
        """
        return self._controller


class VerificationMethod(BaseMethod):
    """Did verification method."""

    class Meta:
        """Did verification method meta."""

    schema_class = "VerificationMethodSchema"

    def __init__(
        self,
        id=None,
        type=None,
        controller=None,
        purpose=None,
        public_key_jwk=None,
        public_key_multibase=None,
        private_key_jwk=None,
        private_key_multibase=None,
    ) -> None:
        super().__init__(id, type, controller, purpose)
        self._public_key_jwk = public_key_jwk
        self._public_key_multibase = public_key_multibase
        self._private_key_jwk = private_key_jwk
        self._private_key_multibase = private_key_multibase

    @property
    def public_key_jwk(self):
        """."""
        return self._public_key_jwk

    @property
    def public_key_multibase(self):
        """."""
        return self._public_key_multibase

    @property
    def private_key_jwk(self):
        """."""
        return self._private_key_jwk

    @property
    def private_key_multibase(self):
        """."""
        return self._private_key_multibase


class VerificationMethodSchema(BaseModelSchema):
    """"""
    class Meta:
        """Did secret schema metadata."""

        model_class = VerificationMethod
        unknown = EXCLUDE

    public_key_jwk = fields.Str(
        required=False,
        description="",
    )
    public_key_multibase = fields.Str(
        required=False,
        description="",
    )
    private_key_jwk = fields.Str(
        required=False,
        description="",
    )
    private_key_multibase = fields.Str(
        required=False,
        description="",
    )


class DIDSecret(BaseModel):
    """Did secret class"""

    class Meta:
        """Did secret meta."""

    schema_class = "DIDSecretSchema"

    def __init__(self, did, options, method: VerificationMethod):
        """"""
        super().__init__()
        self._did = did
        self._options = options
        self._verification_methods = [method]


class DIDSecretSchema(BaseModelSchema):
    """Did secret schema."""

    class Meta:
        """Did secret schema metadata."""

        model_class = DIDSecret
        unknown = INCLUDE

    did = fields.Str(
        required=True,
        description="Registration state",
    )
    options = fields.Str(
        required=False,
        description="Did identifier",
    )
    verification_methods = fields.List(
        fields.Nested(
            VerificationMethodSchema(),
            required=False,
            description="Did document",
        ),
        required=True,
        description="List of verification methods",
    )
