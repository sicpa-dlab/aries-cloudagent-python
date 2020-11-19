"""Handler for incoming mediation request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import MediationManager, MediationManagerError
from ..messages.mediate_request import MediationRequest
from ....problem_report.v1_0.message import ProblemReport


class MediationRequestHandler(BaseHandler):
    """Handler for incoming mediation request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationRequest)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")

        mgr = MediationManager(context)
        try:
            record = await mgr.receive_request(context.message)
            record, grant = await mgr.grant_request(record)
            await responder.send_reply(grant)
            record.routing_keys = grant.routing_keys
            record.endpoint = grant.endpoint
            await record.save(context,
                reason="Mediation request granted",
                webhook=True)
        except MediationManagerError:
            await responder.send_reply(
                ProblemReport(
                    explain_ltxt="Mediation request already exists from this connection."
                )
            )
