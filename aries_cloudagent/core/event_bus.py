"""A simple event bus."""

import logging

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
        self._topic = f"outbound/message/target/{value}"

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
        topic = f"outbound/message/did/{target.did}"
        payload = message
        super().__init__(topic, payload)


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
