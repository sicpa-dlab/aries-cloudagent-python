"""Handler for incoming mediation-granted-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import MediationManager
from ..messages.mediate_grant import MediationGrant
from ..models.mediation_record import MediationRecord


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
        _record = await MediationRecord.retrieve_by_id(
            context, context.mediation_id
        )
        await mgr.granted_request(
            mediation=_record,
            endpoint=context.endpoint,
            routing_did_verkey=context.routing_keys
        )
