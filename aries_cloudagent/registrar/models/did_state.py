from enum import Enum

from marshmallow import EXCLUDE, fields, validate

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import DIDValidation


class RegistrationState(Enum):
    """States of registration."""

    FINISHED = "finished"
    FAILED = "failed"
    ACTION = "action"
    WAIT = "wait"


class DIDState(BaseModel):
    """Did state."""

    class Meta:
        """Did state metadata."""

        schema_class = "DidStateSchema"

    def __init__(self, state, did, secret, document):
        super().__init__()
        self._state: RegistrationState = state or RegistrationState.WAIT
        self._did = did
        self._secret = secret
        self._document = document

    @property
    def state(self) -> RegistrationState:
        """Get state."""
        return self._state

    @state.setter
    def state(self, state: RegistrationState):
        """Set state"""
        self._state = RegistrationState(state)

    @property
    def did(self):
        """Get did."""
        return self._did

    @property
    def secret(self):
        """Get secret."""
        return self._secret

    @property
    def document(self):
        """Get document"""
        return self._document


class DidStateSchema(BaseModelSchema):
    """Did state schema."""

    class Meta:
        """Did state schema metadata."""

        model_class = DIDState
        unknown = EXCLUDE

    state = fields.Str(
        validate=validate.OneOf([state.value for state in RegistrationState]),
        required=True,
        description="Registration state",
    )
    did = fields.Str(
        required=False,
        description="Did identifier",
        validate=validate.Regexp(DIDValidation.PATTERN),  # TODO: do better validation
    )
    secret = fields.Dict(
        keys=fields.Str(),
        values=fields.Str(),
        required=False,
        description="Did secret",
    )
    document = fields.Dict(
        required=False,
        description="Did document",
        keys=fields.Str(),
        values=fields.Str(),
        allow_none=True,
    )
