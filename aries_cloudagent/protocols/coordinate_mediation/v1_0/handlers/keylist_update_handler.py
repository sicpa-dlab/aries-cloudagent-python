"""Handler for keylist-update messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....storage.error import StorageNotFoundError
from ....problem_report.v1_0.message import ProblemReport
from ..manager import MediationManager, MediationNotGrantedError
from ..messages.keylist_update import KeylistUpdate
from ..models.mediation_record import MediationRecord
from ..messages.inner.keylist_updated import KeylistUpdated
from ..messages.inner.keylist_update_rule import KeylistUpdateRule

class KeylistUpdateHandler(BaseHandler):
    """Handler for keylist-update messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle keylist-update messages."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdate)

        if not context.connection_ready:
            raise HandlerException("Cannot update routes: no active connection")

        session = await context.session()
        mgr = MediationManager(session)
        try:
            mediation_record = await MediationRecord.retrieve_by_connection_id(
                session, context.connection_record.connection_id
            )
            response = await mgr.update_keylist(
                mediation_record,
                updates=context.message.updates
            )
            await responder.send_reply(response)
            for updated in response.updated:
                if updated.result != KeylistUpdated.RESULT_SUCCESS:
                    continue
                if updated.action == KeylistUpdateRule.RULE_ADD:
                    mediation_record.recipient_keys.append(updated.recipient_key)
                if updated.action == KeylistUpdateRule.RULE_REMOVE:
                    mediation_record.recipient_keys.remove(updated.recipient_key)
            await mediation_record.save(
                session,
                reason="keylist update response stored in mediation record",
                webhook=True
            )
        except (StorageNotFoundError, MediationNotGrantedError):
            await responder.send_reply(
                ProblemReport(
                    explain_ltxt="Mediation has not been granted for this connection."
                )
            )
