"""Redis outbound transport."""

import asyncio
import logging
import msgpack
from ....core.event_bus import Event
from ....core.profile import Profile

import aioredis

from .base import BaseOutboundQueue, OutboundQueueError


class RedisOutboundQueue(BaseOutboundQueue):
    """Redis outbound transport class."""

    protocol = "redis"

    def __init__(self, connection: str, prefix: str = None) -> None:
        """Set initial state."""
        super().__init__(connection, prefix)
        self.logger = logging.getLogger(__name__)
        self.redis = None

    def __str__(self):
        """Return string representation of the outbound queue."""
        return (
            f"RedisOutboundQueue("
            f"connection={self.connection}, "
            f"prefix={self.prefix}"
            f")"
        )

    async def start(self):
        """Start the transport."""
        loop = asyncio.get_event_loop()
        self.redis = await aioredis.create_redis_pool(
            self.connection,
            minsize=5,
            maxsize=10,
            loop=loop,
        )
        # raises ConnectionRefusedError if not available
        return self

    async def stop(self):
        """Stop the transport."""
        self.redis.close()
        await self.redis.wait_closed()

    async def push(self, key: bytes, message: bytes):
        """Push a ``message`` to redis on ``key``."""
        try:
            return await self.redis.rpush(key, message)
        except aioredis.RedisError as e:
            raise OutboundQueueError(f"Unexpected redis client exception {e}")

    async def notify(self, profile: Profile, event: Event):
        """Notify subscribers of event.

        Args:
            profile (Profile): context of the event
            event (Event): event to emit

        """

        if not event.endpoint:
            raise OutboundQueueError("No endpoint provided")
        payload = event.payload
        if isinstance(payload, bytes):
            content_type = "application/ssi-agent-wire"
        else:
            content_type = "application/json"
            payload = event.payload.encode(encoding="utf-8")
        message = msgpack.packb(
                {
                    "headers": {"Content-Type": content_type},
                    "endpoint": event.endpoint,
                    "payload": payload,
                }
            )
        key = f"{self.prefix}.outbound_transport".encode()
        return await self.push(key, message)
