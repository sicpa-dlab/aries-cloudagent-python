"""Store a message to send after mediation state changes."""

from .....messaging.models.base_record import BaseRecord
from .....transport.outbound.message import OutboundMessage


class ScheduledMessage(BaseRecord):
    """A message scheduled for delivery after mediation state change."""

    class Meta:
        """ScheduledMessage metadata."""

        schema_class = "ScheduledMessageSchema"

    RECORD_TYPE = "scheduled_message"
    RECORD_TOPIC = "mediation::scheduled_message"
    RECORD_ID_NAME = "scheduled_message_id"
    TAG_NAMES = {"state", "on_message_id", "connection_id"}

    STATE_PENDING = "pending"
    STATE_SENT = "sent"

    def __init__(
        self,
        *,
        scheduled_message_id: str = None,
        state: str = None,
        on_message_id: str = None,
        connection_id: str = None,
        new_state: str = None,
        message: OutboundMessage = None,
        **kwargs,
    ):
        """Init record."""
        super().__init__(scheduled_message_id, state or self.STATE_PENDING, **kwargs)
        self.on_message_id = on_message_id
        self.connection_id = connection_id
        self.new_state = new_state
        self.message = message

    @property
    def record_value(self) -> dict:
        """Return values of record as dictionary."""
        return {"new_state": self.new_state, "message": self.message.serialize()}
