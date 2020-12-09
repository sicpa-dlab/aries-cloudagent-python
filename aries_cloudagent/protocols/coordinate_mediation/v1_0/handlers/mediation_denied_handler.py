"""Handler for incoming mediation-deny-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..models.mediation_record import MediationRecord
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport
from ..messages.mediate_deny import MediationDeny


class MediationDenyHandler(BaseHandler):
    """Handler for incoming mediation denied messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationDeny)

        if not context.connection_ready:
            raise HandlerException(
                "Invalid client mediation denied response: no active connection")
        try:
            session = await context.session()
            _record = await MediationRecord.retrieve_by_connection_id(
                session, context.connection_record.connection_id
            )
            _record.state = MediationRecord.STATE_DENIED
            _record.mediator_terms = context.message.mediator_terms
            _record.recipient_terms = context.message.recipient_terms
            await _record.save(session,
                               reason="Mediation request denied",
                               webhook=True)
        except StorageNotFoundError:
            await responder.send_reply(
                ProblemReport(
                    explain_ltxt="Invalid client mediation denied"
                    "response: no mediation requested"
                )
            )
            raise HandlerException("Invalid client mediation denied"
                                   " response: no mediation requested")
