"""Manager for multitenancy."""

from typing import Optional, cast

from aries_cloudagent.core import profile
from aries_cloudagent.multitenant.error import WalletKeyMissingError
from aries_cloudagent.protocols.coordinate_mediation.v1_0.manager import \
    MediationManager
from aries_cloudagent.protocols.coordinate_mediation.v1_0.models.mediation_record import \
    MediationRecord
from aries_cloudagent.protocols.routing.v1_0.models.route_record import \
    RouteRecord
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.wallet.base import BaseWallet

from ..config.injection_context import InjectionContext
from ..config.wallet import wallet_config
from ..core.profile import Profile, ProfileSession
from ..multitenant.base import BaseMultitenantManager, MultitenantManagerError
from ..wallet.models.wallet_record import WalletRecord
from .cache import ProfileCache


class MultitenantManager(BaseMultitenantManager):
    """Class for handling multitenancy."""

    def __init__(self, profile: Profile):
        """Initialize default multitenant Manager.

        Args:
            profile: The profile for this manager
        """
        self._profile = profile
        if not profile:
            raise MultitenantManagerError("Missing profile")

        self._profiles = ProfileCache(100)

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile.

        Returns:
            The profile for this manager

        """
        return self._profile

    async def get_default_mediator(self) -> Optional[MediationRecord]:
        """Retrieve the default mediator used for subwallet routing.

        Returns:
            Optional[MediationRecord]: retrieved default mediator or None if not set

        """
        async with self.profile.session() as session:
            return await MediationManager(session).get_default_mediator()

    async def _wallet_name_exists(
        self, session: ProfileSession, wallet_name: str
    ) -> bool:
        """
        Check whether wallet with specified wallet name already exists.

        Besides checking for wallet records, it will also check if the base wallet

        Args:
            session: The profile session to use
            wallet_name: the wallet name to check for

        Returns:
            bool: Whether the wallet name already exists

        """
        # wallet_name is same as base wallet name
        if session.settings.get("wallet.name") == wallet_name:
            return True

        # subwallet record exists, we assume the wallet actually exists
        wallet_records = await WalletRecord.query(session, {"wallet_name": wallet_name})
        if len(wallet_records) > 0:
            return True

        return False

    async def get_wallet_profile(self, base_context: InjectionContext, wallet_record: WalletRecord, extra_settings: dict = None, *, provision=False) -> Profile:
        """Get profile for a wallet record.

        Args:
            base_context: Base context to extend from
            wallet_record: Wallet record to get the context for
            extra_settings: Any extra context settings

        Returns:
            Profile: Profile for the wallet record

        """
        if extra_settings is None:
            extra_settings = {}
        wallet_id = wallet_record.wallet_id

        if not self._profiles.has(wallet_id):
            # Extend base context
            context = base_context.copy()

            # Settings we don't want to use from base wallet
            reset_settings = {
                "wallet.recreate": False,
                "wallet.seed": None,
                "wallet.rekey": None,
                "wallet.name": None,
                "wallet.type": None,
                "mediation.open": None,
                "mediation.invite": None,
                "mediation.default_id": None,
                "mediation.clear": None,
            }
            extra_settings["admin.webhook_urls"] = self.get_webhook_urls(
                base_context, wallet_record
            )

            context.settings = (
                context.settings.extend(reset_settings)
                .extend(wallet_record.settings)
                .extend(extra_settings)
            )

            # TODO: add ledger config
            profile, _ = await wallet_config(context, provision=provision)
            await self._profiles.put(wallet_id, profile)

        return self._profiles.get(wallet_id)

    async def create_wallet(
        self,
        settings: dict,
        key_management_mode: str,
    ) -> WalletRecord:
        """Create new wallet and wallet record.

        Args:
            settings: The context settings for this wallet
            key_management_mode: The mode to use for key management. Either "unmanaged"
                to not store the wallet key, or "managed" to store the wallet key

        Raises:
            MultitenantManagerError: If the wallet name already exists

        Returns:
            WalletRecord: The newly created wallet record

        """
        wallet_key = settings.get("wallet.key")
        wallet_name = settings.get("wallet.name")

        # base wallet context
        async with self.profile.session() as session:
            # Check if the wallet name already exists to avoid indy wallet errors
            if wallet_name and await self._wallet_name_exists(session, wallet_name):
                raise MultitenantManagerError(
                    f"Wallet with name {wallet_name} already exists"
                )

            # In unmanaged mode we don't want to store the wallet key
            if key_management_mode == WalletRecord.MODE_UNMANAGED:
                del settings["wallet.key"]
            # create and store wallet record
            wallet_record = WalletRecord(
                settings=settings, key_management_mode=key_management_mode
            )

            await wallet_record.save(session)

        # provision wallet
        profile = await self.get_wallet_profile(
            self.profile.context,
            wallet_record,
            {
                "wallet.key": wallet_key,
            },
            provision=True,
        )

        # subwallet context
        async with profile.session() as session:
            wallet = session.inject(BaseWallet)
            public_did_info = await wallet.get_public_did()

            if public_did_info:
                await self.add_key(
                    wallet_record.wallet_id, public_did_info.verkey, skip_if_exists=True
                )

        return wallet_record

    async def remove_wallet(self, wallet_id: str, wallet_key: str = None):
        """Remove the wallet with specified wallet id.

        Args:
            wallet_id: The wallet id of the wallet record
            wallet_key: The wallet key to open the wallet.
                Only required for "unmanaged" wallets

        Raises:
            WalletKeyMissingError: If the wallet key is missing.
                Only thrown for "unmanaged" wallets

        """
        async with self.profile.session() as session:
            wallet = cast(
                WalletRecord,
                await WalletRecord.retrieve_by_id(session, wallet_id),
            )

            wallet_key = wallet_key or wallet.wallet_key
            if wallet.requires_external_key and not wallet_key:
                raise WalletKeyMissingError("Missing key to open wallet")

            profile = await self.get_wallet_profile(
                self.profile.context,
                wallet,
                {"wallet.key": wallet_key},
            )

            self._profiles.remove(wallet_id)
            await profile.remove()

            # Remove all routing records associated with wallet
            storage = session.inject(BaseStorage)
            await storage.delete_all_records(
                RouteRecord.RECORD_TYPE, {"wallet_id": wallet.wallet_id}
            )

            await wallet.delete_record(session)

    async def add_key(
        self, wallet_id: str, recipient_key: str, *, skip_if_exists: bool = False
    ):
        """
        Add a wallet key to map incoming messages to specific subwallets.

        Args:
            profile: The wallet profile instance

        """
        wallet_id = profile.settings.get("wallet.id")
        del self._instances[wallet_id] # TODO: FixME...
        await profile.remove()
