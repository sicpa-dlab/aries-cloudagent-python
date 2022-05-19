"""Handler for keylist-update-response message."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..messages.keylist_update_response import KeylistUpdateResponse
from ..manager import MediationManager
from ..models.scheduled_message import ScheduledMessage
from .....connections.models.conn_record import ConnRecord
from .....storage.error import StorageNotFoundError


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

        mgr = MediationManager(context.profile)
        await mgr.store_update_results(
            context.connection_record.connection_id, context.message.updated
        )

        async with context.session() as session:
            scheduled_messages = await ScheduledMessage.retrieve_by_trigger_thread_id(
                session, context.message._thread_id
            )
            for message in scheduled_messages:
                self._logger.debug("Sending previously scheduled message: %s", message)
                await responder.send_outbound(message.message)
                if message.new_state:
                    try:
                        message_recip_rec = await ConnRecord.retrieve_by_id(
                            session, message.connection_id
                        )
                        message_recip_rec.state = message.new_state
                        await message_recip_rec.save(session)
                        self._logger.debug(
                            "Updated state from previously scheduled message", message
                        )
                    except StorageNotFoundError:
                        self._logger.exception(
                            "Failed to retrieve connection associated with "
                            "scheduled message: %s",
                            message.scheduled_message_id,
                        )
