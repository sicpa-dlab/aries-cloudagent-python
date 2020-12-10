"""Handler for keylist-update-response message."""
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ..messages.keylist_update_response import KeylistUpdateResponse
from ..messages.inner.keylist_updated import KeylistUpdated
from ..messages.inner.keylist_update_rule import KeylistUpdateRule
from .....storage.base import StorageNotFoundError
from ..models.mediation_record import MediationRecord
from ..manager import MediationManager

class KeylistUpdateResponseHandler(BaseHandler):
    """Handler for keylist-update-response message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle keylist-update-response message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdateResponse)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")
        # TODO: resolve duplicate logic here
        # store keylists in mediation_record
        mediation_record = None
        session = await context.session()
        mgr = MediationManager(session)
        try:
            mediation_record = await MediationRecord.retrieve_by_connection_id(
                session, context.connection_record.connection_id
            )
        except StorageNotFoundError as err:
            raise HandlerException('No mediation found for keylist.') from err
        for updated in context.message.updated:
            if updated.result != KeylistUpdated.RESULT_SUCCESS:
                continue
            if updated.action == KeylistUpdateRule.RULE_ADD:
                mediation_record.recipient_keys.append(updated.recipient_key)
            if updated.action == KeylistUpdateRule.RULE_REMOVE:
                mediation_record.recipient_keys.remove(updated.recipient_key)
        await mediation_record.save(
            session,
            reason="keylist update response stored in mediation record"
        )
        # store keylists in ... routes?
        await mgr.store_update_results(
            context.connection_record.connection_id, context.message.updated
        )
