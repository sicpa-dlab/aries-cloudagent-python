from aries_cloudagent.core.profile import Profile
from aries_cloudagent.core.transport_events import (OutboundMessage,
                                                    OutboundMessageEvent,
                                                    OutboundStatusEvent)
from aries_cloudagent.transport.inbound.manager import InboundTransportManager
from aries_cloudagent.transport.inbound.message import InboundMessage
from aries_cloudagent.transport.outbound.status import OutboundSendStatus

from ..transport.outbound.queue.base import BaseOutboundQueue


class OutboundMessageRouter:
    """Outbound Message Router."""

    def __init__(self):
        pass

    async def outbound_message_router(
        self,
        profile: Profile,
        outbound: OutboundMessage,
        inbound: InboundMessage = None,
    ):
        """Emit outbound message event."""
        if (
            not outbound.target
            and outbound.reply_to_verkey
            and not outbound.reply_from_verkey
            and inbound
        ):
            outbound.reply_from_verkey = inbound.receipt.recipient_verkey

        await profile.notify(event=OutboundMessageEvent(outbound))

    async def outbound_message_event_listener(
        self,
        profile: Profile,
        event: OutboundMessageEvent,
    ):
        """Handle outbound message event.

        Listens for outbound message events, processes them, and emits outbound
        send status.

        Args:
            profile: The active profile for the request
            message: An outbound message to be sent
            inbound: The inbound message that produced this response, if available
        """
        outbound = event.outbound
        if not outbound.target and outbound.reply_to_verkey:
            inbound_transport_manager = profile.inject(
                InboundTransportManager, required=False
            )
            # return message to an inbound session
            if inbound_transport_manager.return_to_session(outbound):
                await profile.notify(
                    event=OutboundStatusEvent(
                        OutboundSendStatus.SENT_TO_SESSION, outbound
                    ),
                )
                return

        if not outbound.to_session_only:
            queue_outbound = profile.inject(BaseOutboundQueue, required=False)
            status = await queue_outbound(profile, outbound)
            await profile.notify(event=OutboundStatusEvent(status, outbound))
