"""Base classes for the queue module."""
from abc import abstractmethod
import asyncio
from typing import Any

from ....core.profile import Profile
from ...error import TransportError
from ....core.event_bus import EventBus, Event


class OutboundMessageEvent(Event):
    protocol = None
    endpoint = None

    def __init__(self, topic: str, payload: Any = None, endpoint: str =None):

        super().__init__(topic, payload)
        self.endpoint = endpoint





class BaseOutboundQueue(EventBus):
    """Base class for the outbound queue generic type."""

    protocol = None  # string value representing protocol, e.g. "redis"

    def __init__(self, connection: str, prefix: str = None):
        """Initialize base queue type."""
        super().__init__()
        self.connection = connection
        self.prefix = prefix or "acapy"

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()

    async def __aexit__(self, err_type, err_value, err_t):
        """Async context manager exit."""
        if err_type and err_type != asyncio.CancelledError:
            self.logger.exception("Exception in outbound queue")
        await self.stop()

    @abstractmethod
    async def start(self):
        """Start the queue."""

    @abstractmethod
    async def stop(self):
        """Stop the queue."""

    @abstractmethod
    async def push(self, key: bytes, message: bytes):
        """Push a ``message`` to queue on ``key``."""

    @abstractmethod
    async def notify(self, profile: Profile, event: Event):
        """Produce an Event in the queue."""

    def subscribe(self, pattern, processor):
        """Not implemented due it is an outbound class."""
        raise OutboundQueueNotImplementedMethod("Not implemented for this class")

    def unsubscribe(self, pattern, processor):
        """Not implemented due it is an outbound class."""
        raise OutboundQueueNotImplementedMethod("Not implemented for this class")


class OutboundQueueError(TransportError):
    """Generic outbound transport error."""


class OutboundQueueNotImplementedMethod(TransportError):
    """Generic outbound transport error."""
