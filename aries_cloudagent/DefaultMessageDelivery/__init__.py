""" initialize Message Delivery plugin """
import logging

from ..config.injection_context import InjectionContext
from ..core.event_bus import EventBus
from collections import OrderedDict


LOGGER = logging.getLogger(__name__)
ACAPY_OUTBOUND_MESSAGE_EVENT_TOPIC = "acapy::outbound::message"
topics: OrderedDict = {}  # TODO: add topics and listeners


async def setup(context: InjectionContext):
    """subscribe listeners to topics"""
    event_bus = context.inject(EventBus, required=False)
    if event_bus:
        for topic, listener in topics:
            event_bus.subscribe(topic, listener)
