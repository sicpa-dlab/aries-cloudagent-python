"""Classes for configuring the default injection context."""

from vc.ld_proofs.suites.bbs_bls_signature_proof_2020 import BbsBlsSignatureProof2020
from ..vc.ld_proofs.suites.bbs_bls_signature_2020 import BbsBlsSignature2020
from ..vc.ld_proofs.suites.ed25519_signature_2018 import Ed25519Signature2018
from ..vc.ld_proofs.suites.registry import LDProofSuiteRegistry

from ..cache.base import BaseCache
from ..cache.in_memory import InMemoryCache
from ..core.event_bus import EventBus
from ..core.goal_code_registry import GoalCodeRegistry
from ..core.plugin_registry import PluginRegistry
from ..core.profile import ProfileManager, ProfileManagerProvider
from ..core.protocol_registry import ProtocolRegistry
from ..protocols.actionmenu.v1_0.base_service import BaseMenuService
from ..protocols.actionmenu.v1_0.driver_service import DriverMenuService
from ..protocols.didcomm_prefix import DIDCommPrefix
from ..protocols.introduction.v0_1.base_service import BaseIntroductionService
from ..protocols.introduction.v0_1.demo_service import DemoIntroductionService
from ..resolver.did_resolver import DIDResolver
from ..tails.base import BaseTailsServer
from ..transport.wire_format import BaseWireFormat
from ..utils.dependencies import (is_indy_sdk_module_installed,
                                  is_ursa_bbs_signatures_module_installed)
from ..utils.stats import Collector
from .base_context import ContextBuilder
from .injection_context import InjectionContext
from .provider import CachedProvider, ClassProvider
from .wallet import KeyType


class DefaultContextBuilder(ContextBuilder):
    """Default context builder."""

    async def build_context(self) -> InjectionContext:
        """Build the base injection context; set DIDComm prefix to emit."""
        context = InjectionContext(settings=self.settings)
        context.settings.set_default("default_label", "Aries Cloud Agent")

        if context.settings.get("timing.enabled"):
            timing_log = context.settings.get("timing.log_file")
            collector = Collector(log_path=timing_log)
            context.injector.bind_instance(Collector, collector)

        # Shared in-memory cache
        context.injector.bind_instance(BaseCache, InMemoryCache())

        # Global protocol registry
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())

        # Global goal code registry
        context.injector.bind_instance(GoalCodeRegistry, GoalCodeRegistry())

        # Signature suite registry
        # Register default signatures
        suite =  LDProofSuiteRegistry()
        suite.register(Ed25519Signature2018, [KeyType.ED25519], False)
        if is_ursa_bbs_signatures_module_installed():
            suite.register(BbsBlsSignature2020, [KeyType.BLS12381G1G2], True)
        suite.register(BbsBlsSignatureProof2020, [KeyType.BLS12381G2], True)
        context.injector.bind_instance(LDProofSuiteRegistry,suite)

        # Global event bus
        context.injector.bind_instance(EventBus, EventBus())

        # Global did resolver
        context.injector.bind_instance(DIDResolver, DIDResolver([]))

        await self.bind_providers(context)
        await self.load_plugins(context)

        # Set DIDComm prefix
        DIDCommPrefix.set(context.settings)

        return context

    async def bind_providers(self, context: InjectionContext):
        """Bind various class providers."""

        # Bind global indy pool provider to be able to share pools between wallets
        # It is important the ledger pool provider is available in the base context
        # so it can be shared by all wallet instances. If we set it in the indy sdk
        # profile provider it could mean other wallets won't have access to the provider
        if is_indy_sdk_module_installed():
            from ..ledger.indy import (IndySdkLedgerPool,
                                       IndySdkLedgerPoolProvider)

            context.injector.bind_provider(
                IndySdkLedgerPool,
                CachedProvider(IndySdkLedgerPoolProvider(), ("ledger.pool_name",)),
            )

        context.injector.bind_provider(ProfileManager, ProfileManagerProvider())

        context.injector.bind_provider(
            BaseTailsServer,
            ClassProvider(
                "aries_cloudagent.tails.indy_tails_server.IndyTailsServer",
            ),
        )

        # Register default pack format
        context.injector.bind_provider(
            BaseWireFormat,
            CachedProvider(
                # StatsProvider(
                ClassProvider("aries_cloudagent.transport.pack_format.PackWireFormat"),
                #    (
                #        "encode_message", "parse_message"
                #    ),
                # )
            ),
        )

        # Allow action menu to be provided by driver
        context.injector.bind_instance(BaseMenuService, DriverMenuService(context))
        context.injector.bind_instance(
            BaseIntroductionService, DemoIntroductionService()
        )

    async def load_plugins(self, context: InjectionContext):
        """Set up plugin registry and load plugins."""

        plugin_registry = PluginRegistry(
            blocklist=self.settings.get("blocked_plugins", [])
        )
        context.injector.bind_instance(PluginRegistry, plugin_registry)

        # Register standard protocol plugins
        plugin_registry.register_package("aries_cloudagent.protocols")

        # Currently providing admin routes only
        plugin_registry.register_plugin("aries_cloudagent.holder")
        plugin_registry.register_plugin("aries_cloudagent.ledger")
        plugin_registry.register_plugin(
            "aries_cloudagent.messaging.credential_definitions"
        )
        plugin_registry.register_plugin("aries_cloudagent.messaging.schemas")
        plugin_registry.register_plugin("aries_cloudagent.messaging.jsonld")
        plugin_registry.register_plugin("aries_cloudagent.revocation")
        plugin_registry.register_plugin("aries_cloudagent.resolver")
        plugin_registry.register_plugin("aries_cloudagent.wallet")

        if context.settings.get("multitenant.admin_enabled"):
            plugin_registry.register_plugin("aries_cloudagent.multitenant.admin")

        # Register external plugins
        for plugin_path in self.settings.get("external_plugins", []):
            plugin_registry.register_plugin(plugin_path)

        # Register message protocols
        await plugin_registry.init_context(context)
