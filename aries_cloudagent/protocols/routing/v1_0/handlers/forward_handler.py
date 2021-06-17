"""Handler for incoming forward messages."""

import asyncio
import json

from .....core.event_bus import EventBus
from .....core.transport_events import OutboundStatusEvent
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....protocols.connections.v1_0.manager import ConnectionManager
from ..manager import RoutingManager, RoutingManagerError
from ..messages.forward import Forward


class ForwardHandler(BaseHandler):
    """Handler for incoming forward messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("ForwardHandler called with context %s", context)
        assert isinstance(context.message, Forward)

        if not context.message_receipt.recipient_verkey:
            raise HandlerException("Cannot forward message: unknown recipient")
        self._logger.info(
            "Received forward for: %s", context.message_receipt.recipient_verkey
        )

        packed = context.message.msg
        packed = json.dumps(packed).encode("ascii")
        rt_mgr = RoutingManager(context.profile)
        target = context.message.to

        try:
            recipient = await rt_mgr.get_recipient(target)
        except RoutingManagerError:
            self._logger.exception("Error resolving recipient for forwarded message")
            return

        # load connection
        async with context.session() as session:
            connection_mgr = ConnectionManager(session)
            connection_targets = await connection_mgr.get_connection_targets(
                connection_id=recipient.connection_id
            )
        # TODO: validate that there is 1 target, with 1 verkey. warn otherwise
        connection_verkey = connection_targets[0].recipient_keys[0]

        # Note: not currently vetting the state of the connection here
        self._logger.info(
            f"Forwarding message to connection: {recipient.connection_id}"
        )

        event_bus = context.inject(EventBus)
        with event_bus.wait_for_event(
            context.profile,
            OutboundStatusEvent.topic_re,
            lambda e: e.outbound.payload == packed,
        ) as future_send_status:
            await responder.send(
                packed,
                connection_id=recipient.connection_id,
                target_list=connection_targets,
                reply_to_verkey=connection_verkey,
            )
            send_status = (await asyncio.wait_for(future_send_status, 1)).payload.status

        # emit event that a forward message is received (may trigger webhook event)
        await context.profile.notify(
            topic="acapy::forward::received",
            payload={
                "connection_id": recipient.connection_id,
                "status": send_status.value,
                "recipient_key": context.message.to,
            },
        )
