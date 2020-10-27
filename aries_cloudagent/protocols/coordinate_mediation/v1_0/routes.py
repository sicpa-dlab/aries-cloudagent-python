"""coordinate mediation admin routes."""

# https://github.com/hyperledger/aries-rfcs/tree/master/features/0211-route-coordination#0211-mediator-coordination-protocol
import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate, validates_schema

from .models.mediation_record import MediationRecord, MediationRecordSchema
from .messages.mediate_request import MediationRequest,MediationRequestSchema
from .messages.mediate_grant import  MediationGrantSchema
from .messages.mediate_deny import  MediationDenySchema
from .manager import MediationManager as M_Manager
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ENDPOINT,
    INDY_DID,
    INDY_RAW_PUBLIC_KEY,
    UUIDFour,
    UUID4
)

from ....connections.models.connection_record import ConnectionRecord
from ...problem_report.v1_0 import internal_error
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.error import WalletError
from ....utils.tracing import trace_event, get_timer, AdminAPIMessageTracingSchema

from ...problem_report.v1_0 import internal_error
from ...problem_report.v1_0.message import ProblemReport

from .message_types import SPEC_URI

from aries_cloudagent.protocols.routing.v1_0.models.route_record import RouteRecordSchema


class MediationListSchema(OpenAPISchema):
    """Result schema for mediation list query."""

    results = fields.List(
        fields.Nested(MediationRecordSchema),
        description="List of mediation records",
    )

MEDIATION_REQUEST_ID = {
    "validate": UUIDFour(), 
    "example": UUIDFour.EXAMPLE
    } # TODO: is mediation req id a did?


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
            "'granted' or 'denied'", # TODO: make a dropdown in swagger ui
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
    
    conn_id = fields.UUID(
        description="Connection identifier",
        required=True,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    mediation_id = fields.Str(
        description="Mediation record identifier",
        required=False,
        **MEDIATION_REQUEST_ID,
    )
    state = MEDIATION_STATE
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
        description= "(Optional) One of requested, granted, or denied, corresponding to the different possible states of mediation requests.",
        required= False,
        example= "granted",
    )


def mediation_sort_key(mediation):
    """Get the sorting key for a particular mediation."""
    if mediation["state"] == MediationRecord.STATE_DENIED:
        pfx = "2"
    elif mediation["state"] == MediationRecord.STATE_REQUESTED:
        pfx = "1"
    else: # GRANTED
        pfx = "0"
    return pfx + mediation["created_at"]

@docs(
    tags=["mediation-request"],
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
    for param_name in ( "conn_id",
                        "state"):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    #post_filter = {} # TODO: find out what should be in positive negative filter, thread_id?
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


@docs(tags=["mediation-request"], summary="mediation request, returns a single mediation record.")
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
        _record = await MediationRequestSchema.retrieve_by_id(
            context, _id
        )
        result = _record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        await internal_error(err, web.HTTPBadRequest, _record, outbound_handler)

    return web.json_response(result)

@docs(tags=["mediation-request"], summary="create mediation request record.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationCreateSchema())
@response_schema(MediationRecordSchema(), 201)
async def mediation_record_create(request: web.BaseRequest):
    """
    Request handler for creating a mediation record from attr values.

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
    conn_id = body.get("conn_id")
    mediation_id = body.get("mediation_id")
    state = body.get("state","granted")
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, conn_id
        )
        if not connection_record.is_ready: # TODO: is this the desired behavior for creating a new mediation?
            raise web.HTTPBadRequest(reason="connection identifier must be from a valid connection.")
        mediation_request = MediationRequest(
            #conn_id = conn_id,
            #state = state,
            mediator_terms = mediator_terms,
            recipient_terms = recipient_terms,
            #**{t: body.get(t) for t in MEDIATION_REQUEST_TAGS if body.get(t)},
        )

        trace_event(
            context.settings,
            mediation_request,
            outcome="mediation_record_create.START",
        )

        _manager = M_Manager(context)

        _record, _message = await _manager.receive_request(
            request = mediation_request
        )
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    trace_event(
        context.settings,
        _message,
        outcome="mediation_record_create.END",
        perf_counter=r_time,
    )

    return web.json_response(_record.serialize())


@docs(tags=["mediation-request"], summary="send mediation request.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationCreateSchema())
@response_schema(MediationRecordSchema(), 201)
async def mediation_record_send(request: web.BaseRequest):
    """
    Request handler for sending a mediation record.

    Args:
        request: aiohttp request object
    """

@docs(tags=["mediation-request"], summary="send mediation request.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationRequestSchema())
@response_schema(MediationGrantSchema(), 201)
#@response_schema(MediationDenySchema(), 200) # TODO: handle deny response
async def mediation_record_store(request: web.BaseRequest):
    ""

@docs(tags=["mediation-request"], summary="grant a stored mediation request")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationGrantSchema(), 201)
async def mediation_record_grant(request: web.BaseRequest):
    """
    Request handler for granting a stored mediation record.

    Args:
        request: aiohttp request object
    """

@docs(tags=["mediation-request"], summary="deny a stored mediation request")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationDenySchema(), 201)
async def mediation_record_deny(request: web.BaseRequest):
    """
    Request handler for denying a stored mediation record.

    Args:
        request: aiohttp request object
    """

@docs(tags=["mediation-request"], summary="Remove an existing mediation record")
@match_info_schema(MediationIdSchema())
@response_schema(MediationRecordSchema(), 200)
async def mediation_record_remove(request: web.BaseRequest):
    """
    Request handler for removing a mediation record.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    mediation_id = request.match_info["mediation_id"]

    try:
        mediation = await MediationRecord.retrieve_by_id(context, mediation_id)
        await mediation.delete_record(context)
        # TODO: delete routes keylist for this mediation
        # route_id = # where do we get this id from?
        # route = RouteRecord.retrieve_by_id(context, mediation_id)
        # await route.delete_record(context)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})

class MediationCoordinationProblemReportRequestSchema(OpenAPISchema):
    """Request schema for sending problem report."""

    explain_ltxt = fields.Str(required=True)

@docs(
    tags=["mediation-request"], summary="Send a problem report for mediation coordination."
)
@match_info_schema(MediationIdSchema())
@request_schema(MediationCoordinationProblemReportRequestSchema())
async def mediation_record_problem_report(request: web.BaseRequest):
    """
    Request handler for sending problem report.

    Args:
        request: aiohttp request object

    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    _id = request.match_info["mediation_id"]
    body = await request.json()

    try:
        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    error_result = ProblemReport(explain_ltxt=body["explain_ltxt"])
    error_result.assign_thread_id(_record.thread_id)

    await outbound_handler(error_result, connection_id=_record.connection_id)

    trace_event(
        context.settings,
        error_result,
        outcome="credential_exchange_problem_report.END",
        perf_counter=r_time,
    )

    return web.json_response({})

async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get(
                "/mediation-request/records", 
                mediation_records_list,
                allow_head=False
                ), # -> fetch all mediation request records
            web.get(
                "/mediation-request/records/{mediation_id}", 
                mediation_record_retrieve, 
                allow_head=False
                ), # . -> fetch a single mediation request record
            web.post(
                "/mediation-request/{conn_id}/create",
                mediation_record_create
                ),
            web.post(
                "/mediation-request/{conn_id}/send", 
                mediation_record_send
                ), # -> send mediation request
            web.post(
                "/mediation-request/{conn_id}/request", 
                mediation_record_store
                ), # -> store a mediation request
            web.post(
                "/mediation-request/records/{mediation_id}/grant",
                mediation_record_grant
                ), # -> grant
            web.post(
                "/mediation-request/records/{mediation_id}/deny", 
                mediation_record_deny
                ), # -> deny
            web.post(
                "/mediation-request/records/{mediation_id}/remove", 
                mediation_record_remove
                ), # -> remove record
            web.post(
                "/mediation-request/{mediation_id}/problem-report", 
                mediation_record_problem_report
                ),
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
