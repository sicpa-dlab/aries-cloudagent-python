""" initialize Message Delivery plugin """
import logging

from ..config.injection_context import InjectionContext
from ..core.event_bus import EventBus
from ..core.transport_events import OutboundMessageEvent
from . import OutboundMessageRouter

LOGGER = logging.getLogger(__name__)
topics = {
    OutboundMessageEvent.topic_re: OutboundMessageRouter.outbound_message_event_listener
}


async def setup(context: InjectionContext):
    """ subscribe listeners to topics"""
    event_bus = context.inject(EventBus, required=False)
    for topic, listener in topics:
        event_bus.subscribe(topic, listener)
