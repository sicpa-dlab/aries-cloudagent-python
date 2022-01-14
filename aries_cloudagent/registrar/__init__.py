"""Interfaces and base classes for DID Registrar."""

import logging
from typing import List

from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider

from .base import BaseDidRegistrar

LOGGER = logging.getLogger(__name__)

Registrars = List[BaseDidRegistrar]


async def setup(context: InjectionContext):
    """Set up default registrars."""
    registry = context.inject_or(Registrars)
    if not registry:
        LOGGER.warning("No DID Resolver Registry instance found in context")
        return

    key_registrar = ClassProvider(
        "aries_cloudagent.resolver.default.key.KeyDIDResolver"
    ).provide(context.settings, context.injector)
    await key_registrar.setup(context)
    registry.append(key_registrar)

    if not context.settings.get("ledger.disabled"):
        indy_registrar = ClassProvider(
            "aries_cloudagent.resolver.default.indy.IndyDIDResolver"
        ).provide(context.settings, context.injector)
        await indy_registrar.setup(context)
        registry.append(indy_registrar)
    else:
        LOGGER.warning("Ledger is not configured, not loading IndyDIDResolver")

    web_registrar = ClassProvider(
        "aries_cloudagent.resolver.default.web.WebDIDResolver"
    ).provide(context.settings, context.injector)
    await web_registrar.setup(context)
    registry.append(web_registrar)
