from marshmallow import EXCLUDE, fields

from ..messaging.models.base import BaseModel, BaseModelSchema
from ..registrar.models.did_state import DIDState, DidStateSchema
from ..registrar.models.job import JobRecord


class RegistrationResult(BaseModel):
    """."""

    class Meta:
        """."""

        schema_class = "RegistrationResultSchema"

    def __init__(
        self,
        job: JobRecord = None,
        did_state: DIDState = None,
        registration_metadata: dict = None,
        document_metadata: dict = None,
    ) -> None:
        super().__init__()
        self._job = job
        self._did_state = did_state
        self._registration_metadata = registration_metadata
        self._document_metadata = document_metadata

    @property
    def job(self):
        """."""
        return self._job

    @property
    def did_state(self):
        """."""
        return self._did_state

    @did_state.setter
    def did_state(self, state: DIDState):
        self._did_state = state

    @property
    def registration_metadata(self):
        """."""
        return self._registration_metadata

    @property
    def document_metadata(self):
        """."""
        return self._document_metadata


class RegistrationResultSchema(BaseModelSchema):
    """."""

    class Meta:
        """."""

        model_class = RegistrationResult
        unknown = EXCLUDE

    job = fields.Str(
        required=True,
        description="Did identifier",
    )
    did_state = fields.Nested(DidStateSchema())
    registration_metadata = fields.Dict(
        required=False,
        description="Did document",
        keys=fields.Str(),
        values=fields.Str(),
        allow_none=True,
    )
    documentation_metadata = fields.Dict(
        required=False,
        description="Did document metadata",
        keys=fields.Str(),
        values=fields.Str(),
        allow_none=True,
    )
