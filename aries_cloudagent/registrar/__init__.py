"""Interfaces and base classes for DID Registrar."""

import logging

from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider
from .did_registrars import DIDRegistrars

LOGGER = logging.getLogger(__name__)


async def setup(context: InjectionContext):
    """Set up default registrars."""
    registry = context.inject_or(DIDRegistrars)
    if not registry:
        LOGGER.warning("No DID registrar Registry instance found in context")
        return

    if not context.settings.get("ledger.disabled"):
        registrar = ClassProvider(
            "aries_cloudagent.registrar.default.indy.IndyDIDRegistrar"
        ).provide(context.settings, context.injector)
        await registrar.setup(context)
        registry.register_registrar(registrar)
    else:
        LOGGER.warning("Ledger is not configured, not loading IndyDIDRegistrar")
