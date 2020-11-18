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
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.protocols.coordinate_mediation.v1_0.manager import MediationManager
from ..messages.inner.keylist_update_rule import KeylistUpdateRule
from aries_cloudagent.protocols.coordinate_mediation.v1_0.messages.keylist_update import KeylistUpdate


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
            _record = await MediationRecord.retrieve_by_connection_id(
                context, context.connection_record.connection_id
            )
            _record.state = MediationRecord.STATE_GRANTED
            _record.routing_keys = context.message.routing_keys
            _record.endpoint = context.message.endpoint
            if context.settings.get("mediation.auto_respond_mediation_grant"):
                # create new did for recipient keys
                wallet: BaseWallet = await context.inject(BaseWallet, required=False)
                if not wallet:
                    raise HandlerException("auto respond to mediation grant with no wallet:"
                                   " access denied to create a did for keylist update.")
                info = await wallet.create_local_did(metadata={"mediation_invitation":True})
                # send a update keylist message with new recipient keys.
                updates = [
                    KeylistUpdateRule(
                        recipient_key=info.verkey,
                        action=KeylistUpdateRule.RULE_ADD
                        )
                    ]
                mgr = MediationManager(context)
                update_keylist_request = KeylistUpdate(updates=updates)
                await responder.send_reply(update_keylist_request)
            await _record.save(context,
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
