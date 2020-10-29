"""Handler for incoming route-update-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import MediationManager
from ..messages.mediate_grant import MediationGrant


class MediationGrantHandler(BaseHandler):
    """Handler for incoming mediation grant messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationGrant)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")
        # TODO: Check if mediation record exists
        mgr = MediationManager(context)
        record = await mgr.receive_request(
            context.connection_record.connection_id,
            context.message
            )
        if context.settings.get("mediation.open", False):
            grant = await mgr.grant_request(record)
            await responder.send_reply(grant)
