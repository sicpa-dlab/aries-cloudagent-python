from marshmallow import EXCLUDE, fields

from ..messaging.models.base import BaseModel, BaseModelSchema
from ..registrar.models.did_state import DIDState, DidStateSchema
from ..registrar.models.job import JobRecord


class RegistrationResult(BaseModel):
    """Registration result object."""

    class Meta:
        """Registration result meta class."""

        schema_class = "RegistrationResultSchema"

    def __init__(
        self,
        job_id: str = None,
        did_state: DIDState = None,
        registration_metadata: dict = None,
        document_metadata: dict = None,
    ) -> None:
        super().__init__()
        self._job_id = job_id
        self._did_state = did_state
        self._registration_metadata = registration_metadata
        self._document_metadata = document_metadata

    @property
    def job(self):
        """Identifier of registration job."""
        return self._job_id

    @property
    def did_state(self):
        """Did state."""
        return self._did_state

    @did_state.setter
    def did_state(self, state: DIDState):
        """Did state setter."""
        self._did_state = state

    @property
    def registration_metadata(self):
        """Registration meta data."""
        return self._registration_metadata

    @property
    def document_metadata(self):
        """Document meta data."""
        return self._document_metadata


class RegistrationResultSchema(BaseModelSchema):
    """Registration result schema."""

    class Meta:
        """Registration result meta class."""

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
