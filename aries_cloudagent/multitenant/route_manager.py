"""Multitenancy route manager."""


import logging
from typing import List, Optional, Tuple
from aries_cloudagent.core.profile import Profile
from aries_cloudagent.messaging.responder import BaseResponder

from aries_cloudagent.protocols.coordinate_mediation.v1_0.manager import (
    MediationManager,
)
from aries_cloudagent.protocols.routing.v1_0.manager import RoutingManager
from aries_cloudagent.protocols.routing.v1_0.models.route_record import RouteRecord
from aries_cloudagent.storage.error import StorageNotFoundError

from ..protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from ..protocols.coordinate_mediation.v1_0.route_manager import RouteManager


LOGGER = logging.getLogger(__name__)


class MultitenantRouteManager(RouteManager):
    """Multitenancy route manager."""

    def __init__(self, root_profile: Profile, sub_profile: Profile, wallet_id: str):
        """Initialize multitenant route manager."""
        self.root_profile = root_profile
        self.wallet_id = wallet_id
        super().__init__(sub_profile)

    @property
    def sub_profile(self) -> Profile:
        """Return reference to sub wallet profile."""
        return self.profile

    async def get_base_wallet_mediator(self) -> Optional[MediationRecord]:
        """Get base wallet's default mediator."""
        return await MediationManager(self.root_profile).get_default_mediator()

    async def _route_for_key(
        self,
        recipient_key: str,
        mediation_record: Optional[MediationRecord] = None,
        *,
        skip_if_exists: bool = False,
        replace_key: Optional[str] = None,
    ):
        LOGGER.info(
            f"Add route record for recipient {recipient_key} to wallet {self.wallet_id}"
        )
        routing_mgr = RoutingManager(self.root_profile)
        mediation_mgr = MediationManager(self.root_profile)
        # If base wallet had mediator, only notify that mediator.
        # Else, if subwallet has mediator, notify that mediator.
        base_mediation_record = await self.get_base_wallet_mediator()
        mediation_record = base_mediation_record or mediation_record

        if skip_if_exists:
            try:
                async with self.root_profile.session() as session:
                    await RouteRecord.retrieve_by_recipient_key(session, recipient_key)

                # If no error is thrown, it means there is already a record
                return None
            except (StorageNotFoundError):
                pass

        await routing_mgr.create_route_record(
            recipient_key=recipient_key, internal_wallet_id=self.wallet_id
        )

        # External mediation
        keylist_updates = None
        if mediation_record:
            keylist_updates = await mediation_mgr.add_key(recipient_key)
            if replace_key:
                keylist_updates = await mediation_mgr.remove_key(
                    replace_key, keylist_updates
                )

            responder = self.root_profile.inject(BaseResponder)
            await responder.send(
                keylist_updates, connection_id=mediation_record.connection_id
            )

        return keylist_updates

    async def routing_info(
        self, my_endpoint: str, mediation_record: Optional[MediationRecord] = None
    ) -> Tuple[List[str], str]:
        """Return routing info."""
        routing_keys = []

        base_mediation_record = await self.get_base_wallet_mediator()

        if base_mediation_record:
            routing_keys = base_mediation_record.routing_keys
            my_endpoint = base_mediation_record.endpoint

        if mediation_record:
            routing_keys = [*routing_keys, *mediation_record.routing_keys]
            my_endpoint = mediation_record.endpoint

        return routing_keys, my_endpoint
