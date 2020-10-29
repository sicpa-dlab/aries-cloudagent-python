"""Handler for incoming mediation-deny-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import MediationManager
from ..messages.mediate_grant import MediationGrant
from ..models.mediation_record import MediationRecord


class MediationDenyHandler(BaseHandler):
    """Handler for incoming mediation denied messages."""

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
        await mgr.deny_request(
            mediation=_record,
            mediator_terms=context.mediator_terms,
            recipient_terms=context.recipient_terms
        )
