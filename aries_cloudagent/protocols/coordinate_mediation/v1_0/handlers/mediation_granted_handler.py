"""Handler for incoming mediation-granted-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..messages.mediate_grant import MediationGrant
from ..models.mediation_record import MediationRecord
from aries_cloudagent.storage.error import StorageNotFoundError
from ....connections.v1_0.messages.problem_report import ProblemReport


class MediationGrantHandler(BaseHandler):
    """Handler for incoming mediation grant messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationGrant)
        if not context.connection_ready:
            raise HandlerException(
                "Invalid client mediation grant response: no active connection")
        try:
            session = await context.session()
            _record = await MediationRecord.retrieve_by_connection_id(
                session, context.connection_record.connection_id
            )
            _record.state = MediationRecord.STATE_GRANTED
            _record.routing_keys = context.message.routing_keys
            _record.endpoint = context.message.endpoint
            await _record.save(session,
                               reason="Mediation request granted",
                               webhook=True)
        except StorageNotFoundError:
            await responder.send_reply(
                ProblemReport(
                    explain_ltxt="Invalid client mediation grant"
                    " response: no mediation requested"
                )
            )
            raise HandlerException("Invalid client mediation grant response:"
                                   " no mediation requested")
