"""Interfaces and base classes for DID Registrar."""

import logging

from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider

from .did_registrar_registry import DIDRegistrarRegistry

LOGGER = logging.getLogger(__name__)


async def setup(context: InjectionContext):
    """Set up default registrars."""
    registry = context.inject_or(DIDRegistrarRegistry)
    if not registry:
        LOGGER.warning("No DID Resolver Registry instance found in context")
        return

    key_registrar = ClassProvider(
        "aries_cloudagent.resolver.default.key.KeyDIDResolver"
    ).provide(context.settings, context.injector)
    await key_registrar.setup(context)
    registry.register(key_registrar)

    if not context.settings.get("ledger.disabled"):
        indy_registrar = ClassProvider(
            "aries_cloudagent.resolver.default.indy.IndyDIDResolver"
        ).provide(context.settings, context.injector)
        await indy_registrar.setup(context)
        registry.register(indy_registrar)
    else:
        LOGGER.warning("Ledger is not configured, not loading IndyDIDResolver")

    web_registrar = ClassProvider(
        "aries_cloudagent.resolver.default.web.WebDIDResolver"
    ).provide(context.settings, context.injector)
    await web_registrar.setup(context)
    registry.register(web_registrar)
