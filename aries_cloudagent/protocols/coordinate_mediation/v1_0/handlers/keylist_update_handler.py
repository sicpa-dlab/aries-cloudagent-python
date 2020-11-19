"""Handler for incoming route-update-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from .....storage.error import StorageNotFoundError
from ....problem_report.v1_0.message import ProblemReport

from ..manager import MediationManager
from ..messages.keylist_update import KeylistUpdate
# from ..messages.keylist_update_response import KeylistUpdateResponse
from ..models.mediation_record import MediationRecord
from ..messages.inner.keylist_updated import KeylistUpdated
from ..messages.inner.keylist_update_rule import KeylistUpdateRule


class KeylistUpdateHandler(BaseHandler):
    """Handler for incoming route-update-request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdate)

        if not context.connection_ready:
            raise HandlerException("Cannot update routes: no active connection")

        try:
            record = await MediationRecord.retrieve_by_connection_id(
                context, context.connection_record.connection_id
            )
        except StorageNotFoundError:
            await self.reject(responder)
            return

        if record.state != MediationRecord.STATE_GRANTED:
            await self.reject(responder)
            return

        mgr = MediationManager(context)
        response = await mgr.update_keylist(
            record, updates=context.message.updates
        )
        await responder.send_reply(response)
        for updated in response.updated:
            if updated.result != KeylistUpdated.RESULT_SUCCESS:
                continue
            if updated.action == KeylistUpdateRule.RULE_ADD:
                record.recipient_keys.append(updated.recipient_key)
            if updated.action == KeylistUpdateRule.RULE_REMOVE:
                record.recipient_keys.remove(updated.recipient_key)
        await record.save(
            context,
            reason="keylist update response stored in mediation record",
            webhook=True
        )
        
    async def reject(self, responder: BaseResponder):
        """Send problem report."""
        await responder.send_reply(
            ProblemReport(
                explain_ltxt="Mediation has not been granted for this connection."
            )
        )
