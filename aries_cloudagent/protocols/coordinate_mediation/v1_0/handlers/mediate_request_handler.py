"""Handler for mediate-request message."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ....problem_report.v1_0.message import ProblemReport
from ..manager import MediationManager, MediationAlreadyExists
from ..messages.mediate_request import MediationRequest


class MediationRequestHandler(BaseHandler):
    """Handler for mediate-request message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle mediate-request message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationRequest)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")

        session = await context.session()
        mgr = MediationManager(session)
        try:
            record = await mgr.receive_request(
                context.connection_record.connection_id, context.message
            )
            if context.settings.get("mediation.open", False):
                grant = await mgr.grant_request(record)
                await responder.send_reply(grant)
                # TODO: resolve double logic here,
                # routing keys stored in mediation_record
                record.routing_keys = grant.routing_keys
                record.endpoint = grant.endpoint
                await record.save(session, reason="Mediation request granted")
        except MediationAlreadyExists:
            await responder.send_reply(
                ProblemReport(
                    explain_ltxt="Mediation request already exists from this connection."
                )
            )
