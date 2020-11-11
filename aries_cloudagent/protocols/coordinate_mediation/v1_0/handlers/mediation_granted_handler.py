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
from aries_cloudagent.storage.error import StorageNotFoundError


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
        try:
            _record = await MediationRecord.retrieve_by_connection_id(
                context, context.connection_record.connection_id
            )
            _record.state = MediationRecord.STATE_GRANTED
            _record.routing_keys = context.message.routing_keys
            _record.endpoint = context.message.endpoint
            await _record.save(context, 
                                reason="Mediation request granted",
                                webhook=True)
        except StorageNotFoundError as err:
            raise HandlerException("Invalid mediation granting:"
                                   " no active record")
