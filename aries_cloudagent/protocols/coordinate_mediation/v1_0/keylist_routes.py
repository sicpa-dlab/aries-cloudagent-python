""" routing routes for did_comm forwarding"""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    response_schema,
    request_schema,
)

from .manager import MediationManager as Manager
from .models.mediation_record import (MEDIATION_ID_SCHEMA,
                                      MediationRecord as _Record,
                                      )

from ....messaging.models.openapi import OpenAPISchema
from .message_types import SPEC_URI
from marshmallow import fields, validate
from aries_cloudagent.storage.error import StorageError
from aries_cloudagent.messaging.models.base import BaseModelError
from aries_cloudagent.utils.tracing import get_timer, trace_event
from ....protocols.routing.v1_0.models.route_record import (RouteRecord,
                                                            RouteRecordSchema)
from .messages.keylist_query import KeylistQuery
from .messages.keylist_update_response import KeylistUpdateResponseSchema
from aries_cloudagent.protocols.coordinate_mediation.v1_0.messages.inner.keylist_update_rule import KeylistUpdateRule

# class AllKeyListRecordsPagingSchema(OpenAPISchema):
#     """Parameters and validators for keylist record list query string."""

#     #filter = fields..... TODO: add filtering to handler
#     limit= fields.Integer(
#         description="Number of keylists in a single page.",
#         required=False,
#         example="5",
#     )
#     offset= fields.Integer(
#         description="Page to receive in pagination.",
#         required=False,
#         example="5",
#     )


class KeyListRecordListSchema(OpenAPISchema):
    """Result schema for mediation list query."""

    results = fields.List(  # TODO: order matters, should match sequence?
        fields.Nested(RouteRecordSchema),
        description="List of keylist records",
    )


class _RouteKeySchema(OpenAPISchema):
    """Routing key schema."""

    key = fields.Str(
        description = "Key used for routing."
    )


class KeylistUpdateRequestSchema(OpenAPISchema):
    """keylist update request schema"""

    recipient_key = fields.List(
        fields.Nested(_RouteKeySchema(),
            description = "Keys to be added"
            " or removed."
        )
    )
    action = fields.Str(
        description="update actions",
        required=True,
        validate=validate.OneOf(
            [
                    getattr(KeylistUpdateRule, m)
                    for m in vars(KeylistUpdateRule)
                    if m.startswith("RULE_")
            ]
        ),
        example="'add' or 'remove'",
    )


class MediationIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking mediation request id."""

    mediation_id = MEDIATION_ID_SCHEMA


@docs(
    tags=["keylist"],
    summary="Query keylists, returns list of all keylist records.",
)
# @querystring_schema(AllRecordsQueryStringSchema()) # TODO: add filtering
@response_schema(KeyListRecordListSchema(), 200)
async def list_all_records(request: web.BaseRequest):
    """
    Request handler for searching keylist records.

    Args:
        request: aiohttp request object

    Returns:
        keylists

    """
    context = request.app["request_context"]
    try:
        # TODO: use new keylist models
        records = await RouteRecord.query(context)
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"results": results})


@docs(
    tags=["keylist"],
    summary="send Query keylists request, returns list of all keylist records.",
)
# @querystring_schema(AllRecordsQueryStringSchema()) # TODO: add filtering
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(KeyListRecordListSchema(), 200)
async def send_keylists_request(request: web.BaseRequest):
    """
    Request handler for searching keylist records.

    Args:
        request: aiohttp request object

    Returns:
        keylists

    """
    r_time = get_timer()
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"],
    mediation_id = request.match_info["mediation_id"]
    # body = await request.json()
    record = None
    try:
        record = await _Record.retrieve_by_id(
            context, mediation_id
        )
        # TODO: add pagination to request
        request = KeylistQuery()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        request, connection_id=record.connection_id
    )
    trace_event(
        context.settings,
        request,
        outcome="keylist_update_request.END",
        perf_counter=r_time,
    )
    return web.json_response({"results": request})


@docs(tags=["keylist"], summary="update keylist.")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(KeylistUpdateResponseSchema(), 201)
async def update_keylists(request: web.BaseRequest):
    """
    Request handler for updating keylist.

    Args:
        request: aiohttp request object
    """
    r_time = get_timer()
    context = request.app["request_context"]
    mediation_id = request.match_info["mediation_id"]
    body = await request.json()
    updates = body.get("updates")
    record = None
    try:
        trace_event(
            context.settings, record,
            outcome="keylist_update.START",
        )
        record = await _Record.retrieve_by_id(
            context, mediation_id
        )
        if record.state != _Record.STATE_GRANTED:
            raise web.HTTPBadRequest(reason=("mediation is not granted."))
        mgr = Manager(context)
        response = await mgr.update_keylist(
            record, updates=updates
        )
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    trace_event(
        context.settings,
        response,
        outcome="keylist_update.END",
        perf_counter=r_time,
    )
    return web.json_response(response, status=201)


@docs(tags=["keylist"], summary="update keylist.")
@match_info_schema(MediationIdMatchInfoSchema())
@request_schema(KeylistUpdateRequestSchema())
@response_schema(KeylistUpdateResponseSchema(), 201)
async def send_update_keylists(request: web.BaseRequest):
    """
    Request handler for updating keylist.

    Args:
        request: aiohttp request object
    """
    r_time = get_timer()
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    context = request.app["request_context"]
    mediation_id = request.match_info["mediation_id"]
    body = await request.json()
    recipient_key = body.get("recipient_key")
    action = body.get("action")
    record = None
    try:
        trace_event(
            context.settings, record,
            outcome="keylist_update_request.START",
        )
        record = await _Record.retrieve_by_id(
            context, mediation_id
        )
        if record.state != _Record.STATE_GRANTED:
            raise web.HTTPBadRequest(reason=("mediation is not granted."))
        mgr = Manager(context)
        request = await mgr.update_keylist(
            record, updates=updates
        )
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(
        request, connection_id=record.connection_id
    )
    trace_event(
        context.settings,
        request,
        outcome="keylist_update_request.END",
        perf_counter=r_time,
    )
    return web.json_response(request, status=201)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/keylists/records",
                    list_all_records,
                    allow_head=False),
            # web.get("/keylists/records/pagination",
            #     list_all_records_paging,
            #     allow_head=False),
            # web.get("/keylists/records/{record_id}",
            #     keylist,
            #     allow_head=False),
            # web.get("/keylists/records/{record_id}/pagination",
            #     keylist,
            #     allow_head=False),
            web.post("/keylists/records/{mediation_id}/update",
                     update_keylists),
            web.post("/keylists/request/{mediation_id}/update",
                     send_update_keylists),
            web.post("/keylists/request/{mediation_id}",
                     send_keylists_request),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "routing",
            "description": "List of connection ID to key"
            " list mappings used for message forwarding",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
