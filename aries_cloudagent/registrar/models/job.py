"""DID Registration job."""


from ...core.profile import ProfileSession
from ...messaging.models.base_record import BaseRecord
from .did_state import DIDState, RegistrationState


class JobRecord(BaseRecord):
    """Class representing stored Job state."""

    RECORD_TYPE = "registrar_job"
    RECORD_ID_NAME = "job_id"
    RECORD_TOPIC = "registrar-job"
    TAG_NAMES = {"did", "state", "operation"}

    STATE_FINISHED = RegistrationState.FINISHED.value
    STATE_FAILED = RegistrationState.FAILED.value
    STATE_ACTION = RegistrationState.ACTION.value
    STATE_WAIT = RegistrationState.WAIT.value

    OP_CREATE = "create"
    OP_UPDATE = "update"
    OP_DEACTIVATE = "deactivate"

    def __init__(
        self,
        *,
        job_id: str = None,
        state: DIDState = None,
        did: str = None,
        operation: str = None,
        registration_metadata: dict = None,
        document_metadata: dict = None,
        **kwargs,
    ):
        """Initialize Job Record."""
        super().__init__(job_id, state.state.value or self.STATE_WAIT, **kwargs)
        self.did = did
        self.did_state = state
        self.operation = operation
        self.registration_metadata = registration_metadata
        self.document_metadata = document_metadata

    @property
    def job_id(self) -> str:
        """Get job ID."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Return values of record as dictionary."""
        return {
            "job_id": self.job_id,
            "did": self.did,
            "operation": self.operation,
            "state": self.state,
            "did_state": self.did_state.serialize(),
            "registration_metadata": self.registration_metadata,
            "document_metadata": self.document_metadata,
        }

    @classmethod
    async def retrieve_by_did(cls, session: ProfileSession, did: str) -> "JobRecord":
        """Retrieve a job record by DID."""
        tag_filter = {"did": did}
        return await cls.retrieve_by_tag_filter(session, tag_filter)
