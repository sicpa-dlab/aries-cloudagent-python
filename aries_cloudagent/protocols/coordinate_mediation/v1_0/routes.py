"""coordinate mediation admin routes."""

# https://github.com/hyperledger/aries-rfcs/tree/master/features/0211-route-coordination#0211-mediator-coordination-protocol

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate

from .models.mediation_record import MediationRecord, MediationRecordSchema
from .messages.mediate_request import MediationRequest, MediationRequestSchema
from .messages.mediate_grant import MediationGrantSchema
from .messages.mediate_deny import MediationDenySchema
from .manager import MediationManager as M_Manager
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ENDPOINT,
    UUIDFour,
    UUID4
)

from ....connections.models.connection_record import ConnectionRecord
from ...problem_report.v1_0 import internal_error
from ....storage.error import StorageError, StorageNotFoundError
from ....utils.tracing import trace_event, get_timer

from ...problem_report.v1_0.message import ProblemReport

from .message_types import SPEC_URI


class MediationListSchema(OpenAPISchema):
    """Result schema for mediation list query."""

    results = fields.List(
        fields.Nested(MediationRecordSchema),
        description="List of mediation records",
    )


MEDIATION_REQUEST_ID = {
    "validate": UUIDFour(),
    "example": UUIDFour.EXAMPLE
}  # TODO: is mediation req id a did?


MEDIATION_STATE = fields.Str(
    description="Mediation state (optional)",
    required=False,
    validate=validate.OneOf(
        [
                getattr(MediationRecord, m)
                for m in vars(MediationRecord)
                if m.startswith("STATE_")
        ]
    ),
    example="'request_received',"
    "'granted' or 'denied'",
)


class MediationListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for mediation record list request query string."""

    conn_id = fields.UUID(
        description="Connection identifier (optional)",
        required=False,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    mediator_terms = fields.List(
        fields.Str(
            description="Indicate terms that the mediator "
            "requires the recipient to agree to"
        ),
        required=False,
        description="List of mediator rules for recipient",
    )
    recipient_terms = fields.List(
        fields.Str(
            description="Indicate terms that the recipient "
            "requires the mediator to agree to"
        ),
        required=False,
        description="List of mediator rules for recipient",
    )
    state = MEDIATION_STATE


class MediationCreateSchema(OpenAPISchema):
    """Parameters and validators for create Mediation request query string."""

    # conn_id = fields.UUID(
    #     description="Connection identifier",
    #     required=True,
    #     example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    # )
    # mediation_id = fields.Str(
    #     description="Mediation record identifier",
    #     required=False,
    #     **MEDIATION_REQUEST_ID,
    # )
    # state = MEDIATION_STATE
    mediator_terms = fields.List(
        fields.Str(
            description="Indicate terms that the mediator "
            "requires the recipient to agree to"
        ),
        required=False,
        description="List of mediator rules for recipient",
    )
    recipient_terms = fields.List(
        fields.Str(
            description="Indicate terms that the recipient "
            "requires the mediator to agree to"
        ),
        required=False,
        description="List of recipient rules for mediation",
    )


class AcceptRequestQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept conn-request web-request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)


class MediationIdSchema(OpenAPISchema):
    """Path parameters and validators for request taking mediation id."""

    mediation_id = fields.Str(
        description="Mediation identifier", required=True, example=UUIDFour.EXAMPLE
    )


class MediationsSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection and ref ids."""

    conn_id = fields.Str(
        description="(Optional) Connection ID to retrieve mediation requests from.",
        required=False,
        example=UUIDFour.EXAMPLE
    )

    mediation_id = fields.Str(
        description="(Optional) Mediation identifier",
        required=False,
        example=UUIDFour.EXAMPLE,
    )
    state = fields.Str(
        description="(Optional) One of requested,"
        " granted, or denied, corresponding to"
        " the different possible states of mediation requests.",
        required=False,
        example="granted",
    )


def mediation_sort_key(mediation):
    """Get the sorting key for a particular mediation."""
    if mediation["state"] == MediationRecord.STATE_DENIED:
        pfx = "2"
    elif mediation["state"] == MediationRecord.STATE_REQUEST_RECEIVED:
        pfx = "1"
    else:  # GRANTED
        pfx = "0"
    return pfx + mediation["created_at"]


@docs(
    tags=["mediation"],
    summary="Query mediation requests, returns list of all mediation records.",
)
@querystring_schema(MediationListQueryStringSchema())
@response_schema(MediationListSchema(), 200)
async def mediation_records_list(request: web.BaseRequest):
    """
    Request handler for searching mediation records.

    Args:
        request: aiohttp request object

    Returns:
        The mediation list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    for param_name in ("conn_id",
                       "state"):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    try:
        records = await MediationRecord.query(context, tag_filter)
        results = [record.serialize() for record in records]
        results.sort(key=mediation_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"results": results})


class MediationIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking mediation request id."""

    mediation_id = fields.Str(
        description="mediation request record identifier", required=True, **UUID4
    )


class ConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


@docs(tags=["mediation"], summary="mediation request, returns a single mediation record.")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationRecordSchema(), 200)
async def mediation_record_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching single mediation request record.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    _id = request.match_info["mediation_id"]
    _record = None
    try:
        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        result = _record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        await internal_error(err, web.HTTPBadRequest, _record, outbound_handler)

    return web.json_response(result)


@docs(tags=["mediation"], summary="create mediation request record.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationCreateSchema())
@response_schema(MediationRecordSchema(), 201)
async def mediation_record_create(request: web.BaseRequest):
    """
    Request handler for creating a mediation record locally.

    The internal mediation record will be created without the request
    being sent to any connection. This can be used in conjunction with
    the `oob` protocols to bind messages to an out of band message.

    Args:
        request: aiohttp request object

    Req_Args:
        conn_id: connection id for whom the mediation is for.
        mediation_id:
        state:
        mediator_terms:
        recipient_terms:
    """
    r_time = get_timer()

    context = request.app["request_context"]

    body = await request.json()
    # record parameters
    conn_id = request.match_info["conn_id"]
    # mediation_id = body.get("mediation_id")
    # state = body.get("state", "granted")
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, conn_id
        )
        if not connection_record.is_ready:  # TODO: is this the desired behavior?
            raise web.HTTPBadRequest(
                reason="connection identifier must be from a valid connection.")
        mediation_request = MediationRequest(
            # conn_id = conn_id,
            # state = state,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
            # **{t: body.get(t) for t in MEDIATION_REQUEST_TAGS if body.get(t)},
        )

        trace_event(
            context.settings,
            mediation_request,
            outcome="mediation_record_create.START",
        )

        _manager = M_Manager(context)

        _record = await _manager.receive_request(
            conn_id=conn_id,
            request=mediation_request
        )
        result = _record.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    trace_event(
        context.settings,
        mediation_request,
        outcome="mediation_record_create.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["mediation"], summary="create and send mediation request.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationCreateSchema())
@response_schema(MediationRecordSchema(), 201)
async def mediation_record_send_create(request: web.BaseRequest):
    """
    Request handler for creating a mediation request record and sending.

    The internal mediation record will be created and a request
    sent to the connection.

    Args:
        request: aiohttp request object

    Req_Args:
        conn_id: connection id for whom the mediation is for.
        mediation_id:
        state:
        mediator_terms:
        recipient_terms:
    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    # record parameters
    conn_id = request.match_info["conn_id"]
    # mediation_id = body.get("mediation_id")
    # state = body.get("state", "granted")
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, conn_id
        )
        if not connection_record.is_ready:  # TODO: is this the desired behavior?
            raise web.HTTPBadRequest(
                reason="connection identifier must be from a valid connection.")
        mediation_request = MediationRequest(
            # conn_id = conn_id,
            # state = state,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
            # **{t: body.get(t) for t in MEDIATION_REQUEST_TAGS if body.get(t)},
        )

        trace_event(
            context.settings,
            mediation_request,
            outcome="mediation_record_create.START",
        )

        _manager = M_Manager(context)

        _record = await _manager.prepare_request(
            conn_id=conn_id,
            request=mediation_request
        )
        result = _record.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        mediation_request, connection_id=_record.connection_id
    )

    trace_event(
        context.settings,
        mediation_request,
        outcome="mediation_record_create.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["mediation"], summary="create and send mediation request.")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationRecordSchema(), 201)
async def mediation_record_send(request: web.BaseRequest):
    """
    Request handler for sending a mediation request record.

    Args:
        request: aiohttp request object

    Req_Args:
        conn_id: connection id for whom the mediation is for.
        mediation_id:
        state:
        mediator_terms:
        recipient_terms:
    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    _id = request.match_info["mediation_id"]
    _record = None
    try:
        trace_event(
            context.settings,
            _record,
            outcome="mediation_send.START",
        )

        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        _message = MediationRequest(mediator_terms=_record.mediator_terms,
                                    recipient_terms=_record.recipient_terms)

    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        _message, connection_id=_record.connection_id
    )

    trace_event(
        context.settings,
        _message,
        outcome="mediation_record_send.END",
        perf_counter=r_time,
    )

    # should this return the response form outbound_message_router
    return web.json_response(_record.serialize())


@docs(tags=["mediation"], summary="receive mediation request.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationRequestSchema())
@response_schema(MediationGrantSchema(), 201)
@response_schema(MediationDenySchema(), 200)  # TODO: handle deny response
async def mediation_record_store(request: web.BaseRequest):
    """
        handler for mediation request.

    Args:
        request: aiohttp request object

    Req_Args:
        conn_id: connection id for whom the mediation is for.
        mediation_id:
        state:
        mediator_terms:
        recipient_terms:
    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    # record parameters
    conn_id = request.match_info["conn_id"]
    # mediation_id = body.get("mediation_id")
    # state = body.get("state", "granted")
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, conn_id
        )
        if not connection_record.is_ready:  # TODO: is this the desired behavior?
            raise web.HTTPBadRequest(
                reason="connection identifier must be from a valid connection.")
        mediation_request = MediationRequest(
            # conn_id = conn_id,
            # state = state,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
            # **{t: body.get(t) for t in MEDIATION_REQUEST_TAGS if body.get(t)},
        )

        trace_event(
            context.settings,
            mediation_request,
            outcome="mediation_record_store.START",
        )

        _manager = M_Manager(context)

        _record = await _manager.receive_request(
            conn_id=conn_id,
            request=mediation_request
        )
        mediation_granted = await _manager.grant_request(
            mediation=_record
        )
        result = mediation_granted.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        mediation_granted, connection_id=_record.connection_id
    )

    trace_event(
        context.settings,
        mediation_request,
        outcome="mediation_record_strore.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["mediation"], summary="grant a stored mediation request")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationGrantSchema(), 201)
async def mediation_record_grant(request: web.BaseRequest):
    """
    Request handler for granting a stored mediation record.

    Args:
        request: aiohttp request object
    """
    # TODO: check that request origination point
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    _id = request.match_info["mediation_id"]
    _record = None
    try:
        trace_event(
            context.settings,
            _record,
            outcome="mediation_grant.START",
        )

        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )

        _manager = M_Manager(context)

        _message = await _manager.grant_request(
            mediation=_record
        )
        result = _message.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        _message, connection_id=_record.connection_id
    )

    trace_event(
        context.settings,
        _message,
        outcome="mediation_record_grant.END",
        perf_counter=r_time,
    )
    return web.json_response(result)


@docs(tags=["mediation"], summary="deny a stored mediation request")
@match_info_schema(MediationIdMatchInfoSchema())
@request_schema(MediationDenySchema())
@response_schema(MediationDenySchema(), 201)
async def mediation_record_deny(request: web.BaseRequest):
    """
    Request handler for denying a stored mediation record.

    Args:
        request: aiohttp request object
    """

    # TODO: check that request origination point
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    _id = request.match_info["mediation_id"]
    _record = None

    body = await request.json()
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")

    try:
        trace_event(
            context.settings,
            _record,
            outcome="mediation_deny.START",
        )

        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )

        _manager = M_Manager(context)

        _message = await _manager.deny_request(
            mediation=_record,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms
        )
        result = _message.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        _message, connection_id=_record.connection_id
    )

    trace_event(
        context.settings,
        _message,
        outcome="mediation_deny.END",
        perf_counter=r_time,
    )
    return web.json_response(result)

async def register(app: web.Application):
    """Register routes.

    record represents internal origin, request extrenal origin

    """

    app.add_routes(
        [
            web.get(
                "/mediation/records",
                mediation_records_list,
                allow_head=False
            ),  # -> fetch all mediation request records
            web.get(
                "/mediation/records/{mediation_id}",
                mediation_record_retrieve,
                allow_head=False
            ),  # . -> fetch a single mediation request record
            web.post(
                "/mediation/records/{conn_id}/create",
                mediation_record_create
            ),
            web.post(
                "/mediation/records/{conn_id}/create-send",
                mediation_record_send_create
            ),
            web.post(
                "/mediation/request/{conn_id}/request",
                mediation_record_store
            ),  # -> store a mediation request
            web.post(
                "/mediation/records/{mediation_id}/send",
                mediation_record_send
            ),  # -> send mediation request
            web.post(
                "/mediation/records/{mediation_id}/grant",
                mediation_record_grant
            ),  # -> grant
            web.post(
                "/mediation/records/{mediation_id}/deny",
                mediation_record_deny
            ),  # -> deny
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "mediation",
            "description": "mediation management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
