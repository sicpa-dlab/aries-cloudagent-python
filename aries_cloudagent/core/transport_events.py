"""Transport Events."""

import re
from typing import NamedTuple, Pattern
from ..transport.outbound.message import OutboundMessage
from ..transport.outbound.status import OutboundSendStatus
from .event_bus import BaseEvent


class OutboundMessageEvent(BaseEvent[OutboundMessage]):
    """Event encapsulating an outbound message event."""

    topic: str = "acapy::outbound::message"
    topic_re: Pattern = re.compile(topic)

    def __init__(self, payload: OutboundMessage):
        """Create OutboundMessageEvent."""
        super().__init__(self.topic, payload)

    @property
    def outbound(self) -> OutboundMessage:
        """Alias to payload."""
        assert self.payload
        return self.payload


class OutboundStatusEventPayload(NamedTuple):
    """Payload of OutboundStatusEvent."""

    status: OutboundSendStatus
    outbound: OutboundMessage


class OutboundStatusEvent(BaseEvent[OutboundStatusEventPayload]):
    """Event for reporting status of outbound message handling."""

    topic_root: str = "acapy::outbound::status::"
    topic_re: Pattern = re.compile(topic_root + ".*")

    def __init__(self, status: OutboundSendStatus, outbound: OutboundMessage):
        """Create OutboundStatusEvent."""
        payload = OutboundStatusEventPayload(status, outbound)
        super().__init__(self.topic_root + status.value, payload)

    @property
    def status(self):
        """Access status."""
        return self.payload.status

    @property
    def outbound(self):
        """Access outbound."""
        return self.payload.outbound
