"""Interfaces and base classes for DID Provider."""

import logging

from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider

from .did_provider_registry import DIDProviderRegistry

LOGGER = logging.getLogger(__name__)


async def setup(context: InjectionContext):
    """Set up default providers."""
    registry = context.inject_or(DIDProviderRegistry)
    if not registry:
        LOGGER.warning("No DID Resolver Registry instance found in context")
        return

    key_provider = ClassProvider(
        "aries_cloudagent.provider.default.key.KeyDIDResolver"
    ).provide(context.settings, context.injector)
    await key_provider.setup(context)
    registry.register(key_provider)

    if not context.settings.get("ledger.disabled"):
        indy_provider = ClassProvider(
            "aries_cloudagent.provider.default.indy.IndyDIDResolver"
        ).provide(context.settings, context.injector)
        await indy_provider.setup(context)
        registry.register(indy_provider)
    else:
        LOGGER.warning("Ledger is not configured, not loading IndyDIDResolver")

    web_provider = ClassProvider(
        "aries_cloudagent.provider.default.web.WebDIDResolver"
    ).provide(context.settings, context.injector)
    await web_provider.setup(context)
    registry.register(web_provider)
