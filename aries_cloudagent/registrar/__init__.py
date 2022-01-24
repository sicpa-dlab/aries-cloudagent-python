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
        LOGGER.warning("No DID registrar Registry instance found in context")
        return

    if not context.settings.get("ledger.disabled"):
        registrar = ClassProvider(
            "aries_cloudagent.registrar.default.indy.IndyDIDRegistrar"
        ).provide(context.settings, context.injector)
        await registrar.setup(context)
        registry.append(registrar)
    else:
        LOGGER.warning("Ledger is not configured, not loading IndyDIDRegistrar")
