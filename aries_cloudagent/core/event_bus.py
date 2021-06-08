"""A simple event bus."""

import logging
import re
from itertools import chain
from typing import TYPE_CHECKING, Any, Callable, Dict, Pattern, Sequence, Union

if TYPE_CHECKING:  # To avoid circular import error
    from .profile import Profile

from ..connections.models.connection_target import ConnectionTarget

LOGGER = logging.getLogger(__name__)


class Event:
    """A simple event object."""

    def __init__(self, topic: str, payload: Any = None):
        """Create a new event."""
        self._topic = topic
        self._payload = payload

    @property
    def topic(self):
        """Return this event's topic."""
        return self._topic

    @property
    def payload(self):
        """Return this event's payload."""
        return self._payload

    @payload.setter
    def payload(self, value):
        """Set this event's payload."""
        self._payload = value

    def __eq__(self, other):
        """Test equality."""
        if not isinstance(other, Event):
            return False
        return self._topic == other._topic and self._payload == other._payload

    def __repr__(self):
        """Return debug representation."""
        return "<Event topic={}, payload={}>".format(self._topic, self._payload)


EVENT_PATTERN_QUEUEDOUTBOUNDMESSAGE = re.compile("^acapy::queuedoutboundMessage::(.*)$")
EVENT_PATTERN_OUTBOUNDMESSAGE = re.compile("^acapy::outboundMessage::(.*)$")
"""Outbound message representation."""


class QueuedOutboundMessage(Event):
    """Class representing an outbound message for EventBus"""

    STATE_NEW = "new"
    STATE_PENDING = "pending"
    STATE_ENCODE = "encode"
    STATE_DELIVER = "deliver"
    STATE_RETRY = "retry"
    STATE_DONE = "done"

    @property
    def topic(self):
        """Return this event's topic."""
        return self._topic

    @topic.setter
    def topic(self, value):
        """Set this event's Topic."""
        self._topic = f"outbound/queuedmessage/target/{value}"

    def __init__(
        self,
        profile: Profile,
        message: Any,
        target: ConnectionTarget,
        transport_id: str,
    ):
        """Initialize the queued outbound message."""
        self.profile = profile
        self.endpoint = target and target.endpoint
        self.error: Exception = None
        self.message = message
        self.payload = None
        self.retries = None
        self.retry_at: float = None
        self.state = self.STATE_NEW
        self.target = target
        # TODO: task logic should be implemented in another way
        self.task: asyncio.Task = None
        self.transport_id: str = transport_id
        self.metadata: dict = None
        self.api_key: str = None
        topic = f"outbound/queuedmessage/did/{target.did}"
        payload = message
        super().__init__(topic, payload)


class OutboundMessage(Event):
    """Represents an outgoing message."""

    @property
    def topic(self):
        """Return this event's topic."""
        return self._topic

    @topic.setter
    def topic(self, value):
        """Set this event's Topic."""
        self._topic = f"outbound/message/target/{value}"
    
    def __init__(
        self,
        *,
        connection_id: str = None,
        enc_payload: Union[str, bytes] = None,
        endpoint: str = None,
        payload: Union[str, bytes],
        reply_session_id: str = None,
        reply_thread_id: str = None,
        reply_to_verkey: str = None,
        reply_from_verkey: str = None,
        target: ConnectionTarget = None,
        target_list: Sequence[ConnectionTarget] = None,
        to_session_only: bool = False,
    ):
        """Initialize an outgoing message."""
        self.connection_id = connection_id
        self.enc_payload = enc_payload
        self._endpoint = endpoint
        self.payload = payload
        self.reply_session_id = reply_session_id
        self.reply_thread_id = reply_thread_id
        self.reply_to_verkey = reply_to_verkey
        self.reply_from_verkey = reply_from_verkey
        self.target = target
        self.target_list = list(target_list) if target_list else []
        self.to_session_only = to_session_only
        topic = f"outbound/message/did/{target.did}"
        payload = message
        super().__init__(topic, payload)

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
    
class EventBus:
    """A simple event bus implementation."""

    def __init__(self):
        """Initialize Event Bus."""
        self.topic_patterns_to_subscribers: Dict[Pattern, Sequence[Callable]] = {}

    async def notify(self, profile: "Profile", event: Event):
        """Notify subscribers of event.

        Args:
            profile (Profile): context of the event
            event (Event): event to emit

        """
        # TODO don't block notifier until subscribers have all been called?
        # TODO trigger each processor but don't await?
        # TODO log errors but otherwise ignore?

        LOGGER.debug("Notifying subscribers: %s", event)
        matched = [
            processor
            for pattern, processor in self.topic_patterns_to_subscribers.items()
            if pattern.match(event.topic)
        ]

        for processor in chain(*matched):
            try:
                await processor(profile, event)
            except Exception:
                LOGGER.exception("Error occurred while processing event")

    def subscribe(self, pattern: Pattern, processor: Callable):
        """Subscribe to an event.

        Args:
            pattern (Pattern): compiled regular expression for matching topics
            processor (Callable): async callable accepting profile and event

        """
        LOGGER.debug("Subscribed: topic %s, processor %s", pattern, processor)
        if pattern not in self.topic_patterns_to_subscribers:
            self.topic_patterns_to_subscribers[pattern] = []
        self.topic_patterns_to_subscribers[pattern].append(processor)

    def unsubscribe(self, pattern: Pattern, processor: Callable):
        """Unsubscribe from an event.

        This method is idempotent. Repeated calls to unsubscribe will not
        result in errors.

        Args:
            pattern (Pattern): regular expression used to subscribe the processor
            processor (Callable): processor to unsubscribe

        """
        if pattern in self.topic_patterns_to_subscribers:
            try:
                index = self.topic_patterns_to_subscribers[pattern].index(processor)
            except ValueError:
                return
            del self.topic_patterns_to_subscribers[pattern][index]
            if not self.topic_patterns_to_subscribers[pattern]:
                del self.topic_patterns_to_subscribers[pattern]
            LOGGER.debug("Unsubscribed: topic %s, processor %s", pattern, processor)


class MockEventBus(EventBus):
    """A mock EventBus for testing."""

    def __init__(self):
        """Initialize MockEventBus."""
        super().__init__()
        self.events = []

    async def notify(self, profile: "Profile", event: Event):
        """Append the event to MockEventBus.events."""
        self.events.append((profile, event))
