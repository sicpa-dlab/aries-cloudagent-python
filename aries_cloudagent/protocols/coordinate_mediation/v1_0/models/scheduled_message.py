"""Store a message to send after mediation state changes."""

from typing import Sequence
from marshmallow import fields
from marshmallow.utils import EXCLUDE
from .....core.profile import ProfileSession
from .....messaging.models.base_record import BaseRecord, BaseRecordSchema
from .....transport.outbound.message import OutboundMessage


class ScheduledMessage(BaseRecord):
    """A message scheduled for delivery after mediation state change."""

    class Meta:
        """ScheduledMessage metadata."""

        schema_class = "ScheduledMessageSchema"

    RECORD_TYPE = "scheduled_message"
    RECORD_TOPIC = "mediation::scheduled_message"
    RECORD_ID_NAME = "scheduled_message_id"
    TAG_NAMES = {"state", "trigger_thread_id", "connection_id"}

    STATE_PENDING = "pending"
    STATE_SENT = "sent"

    def __init__(
        self,
        *,
        scheduled_message_id: str = None,
        state: str = None,
        trigger_thread_id: str = None,
        connection_id: str = None,
        new_state: str = None,
        message: OutboundMessage = None,
        **kwargs,
    ):
        """Init record."""
        super().__init__(scheduled_message_id, state or self.STATE_PENDING, **kwargs)
        self.trigger_thread_id = trigger_thread_id
        self.connection_id = connection_id
        self.new_state = new_state
        self.message = message

    @property
    def record_value(self) -> dict:
        """Return values of record as dictionary."""
        return {"new_state": self.new_state, "message": self.message.serialize()}

    @property
    def scheduled_message_id(self) -> str:
        return self.scheduled_message_id

    @classmethod
    async def retrieve_by_trigger_thread_id(
        cls, session: ProfileSession, thread_id: str
    ) -> Sequence["ScheduledMessage"]:
        """Retrieve a scheduled message by triggering thread id."""
        return await cls.query(session, {"trigger_thread_id": thread_id})


class ScheduledMessageSchema(BaseRecordSchema):
    """ScheduledMessage schema."""

    class Meta:
        """Schema metadata."""

        model_class = ScheduledMessage
        unknown = EXCLUDE

    scheduled_message_id = fields.Str(required=False)
    trigger_thread_id = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    new_state = fields.Str(required=True)
    message = fields.Mapping(required=True)
