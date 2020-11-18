"""Handler for incoming mediation keylist update response messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..messages.keylist_update_response import KeylistUpdateResponse
from ..messages.inner.keylist_updated import KeylistUpdated
from ..messages.inner.keylist_update_rule import KeylistUpdateRule
from ....routing.v1_0.models.route_record import RouteRecord
from .....storage.base import StorageNotFoundError
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport
from ..models.mediation_record import MediationRecord


class KeylistUpdateResponseHandler(BaseHandler):
    """Handler for incoming keylist update response messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdateResponse)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")
        mediation_record = None
        try:
            mediation_record = await MediationRecord.retrieve_by_connection_id(
                    context, context.connection_record.connection_id
                )
        except StorageNotFoundError as err:
            raise HandlerException('No mediation found for keylist.') from err
        for updated in context.message.updated:
            if updated.result != KeylistUpdated.RESULT_SUCCESS:
                continue
            if updated.action == KeylistUpdateRule.RULE_ADD:
                mediation_record.recipient_keys.append(updated.recipient_key)
                # record = RouteRecord(
                #     role=RouteRecord.ROLE_CLIENT,
                #     recipient_key=updated.recipient_key,
                #     connection_id=context.connection_record.connection_id
                # )
                # TODO: log success
                # await record.save(context, reason="Route successfully added.")
            if updated.action == KeylistUpdateRule.RULE_REMOVE:
                mediation_record.recipient_keys.remove(updated.recipient_key)
                # try:
                #     records = await RouteRecord.query(
                #         context,
                #         {
                #             'role': RouteRecord.ROLE_CLIENT,
                #             'connection_id': context.connection_record.connection_id,
                #             'recipient_key': updated.recipient_key
                #         }
                #     )
                # except StorageNotFoundError:
                #     raise HandlerException('No such route found.')

                # if len(records) > 1:
                #     raise HandlerException('More than one route record found.')

                # record = records[0]
                # await record.delete_record(context)
        await mediation_record.save(
            context,
            reason="keylist update response stored in mediation record",
            webhook=True
        )