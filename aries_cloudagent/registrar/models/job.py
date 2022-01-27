"""DID Registration job."""

from ...core.profile import ProfileSession
from ...messaging.models.base_record import BaseRecord


class JobRecord(BaseRecord):
    """Class representing stored Job state."""

    RECORD_TYPE = "registrar_job"
    RECORD_ID_NAME = "job_id"
    RECORD_TOPIC = "registrar-job"
    TAG_NAMES = {"did", "state"}

    STATE_CREATED = "created"
    STATE_PENDING = "pending"
    STATE_REGISTERED = "registered"

    def __init__(
        self,
        *,
        job_id: str = None,
        state: str = None,
        did: str = None,
        **kwargs,
    ):
        """Initialize Job Record."""
        super().__init__(job_id, state or self.STATE_CREATED, **kwargs)
        self.did = did

    @property
    def job_id(self) -> str:
        """Get job ID."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Return values of record as dictionary."""
        return {}

    @classmethod
    async def retrieve_by_did(cls, session: ProfileSession, did: str) -> "JobRecord":
        """Retrieve a job record by DID."""
        tag_filter = {"did": did}
        return await cls.retrieve_by_tag_filter(session, tag_filter)
