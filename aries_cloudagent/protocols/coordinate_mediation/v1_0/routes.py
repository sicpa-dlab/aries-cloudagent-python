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
from .messages.mediate_request import  MediationRequestSchema

from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ENDPOINT,
    INDY_DID,
    INDY_RAW_PUBLIC_KEY,
    UUIDFour,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.error import WalletError

from .message_types import SPEC_URI

from aries_cloudagent.protocols.routing.v1_0.models.route_record import RouteRecordSchema


class MediationsListSchema(OpenAPISchema):
    """Result schema for mediations."""

    results = fields.List(
        fields.Nested(MediationRecordSchema()),
        description="List of mediation records",
    )


class MediationRequestSchema(MediationRequestSchema):
    """Request schema for Mediation request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Bypass middleware field validation."""


class MediationGrantSchema(OpenAPISchema):
    """Result schema for a granted Mediation."""

    # connection_id = fields.Str(
    #     description="Connection identifier", example=UUIDFour.EXAMPLE
    # )
    # Mediation = fields.Nested(ConnectionMediationSchema())
    # Mediation_url = fields.Str(
    #     description="Mediation URL",
    #     example="http://192.168.56.101:8020/invite?c_i=eyJAdHlwZSI6Li4ufQ==",
    # )

class MediationDenySchema(OpenAPISchema):
    """Result schema for a denied Mediation."""

    # connection_id = fields.Str(
    #     description="Connection identifier", example=UUIDFour.EXAMPLE
    # )
    # Mediation = fields.Nested(ConnectionMediationSchema())
    # Mediation_url = fields.Str(
    #     description="Mediation URL",
    #     example="http://192.168.56.101:8020/invite?c_i=eyJAdHlwZSI6Li4ufQ==",
    # )

class MediationsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for mediation record list request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    initiator = fields.Str(
        description="mediation initiator",
        required=False,
        validate=validate.OneOf(["self", "external"]),
    )
    Mediation_key = fields.Str(
        description="Mediation key", required=False, **INDY_RAW_PUBLIC_KEY
    )
    #my_did = fields.Str(description="My DID", required=False, **INDY_DID)
    state = fields.Str(
        description="Mediation state",
        required=False,
        validate=validate.OneOf(
            [
                getattr(MediationRecord, m)
                for m in vars(MediationRecord)
                if m.startswith("STATE_")
            ]
        ),
    )
    their_did = fields.Str(description="Their DID", required=False, **INDY_DID)
    # their_role = fields.Str(
    #     description="Their assigned connection role",
    #     required=False,
    #     example="Point of contact",
    # )


class CreateMediationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create Mediation request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (default as per configuration)",
        required=False,
    )
    public = fields.Boolean(
        description="Create Mediation from public DID (default false)", required=False
    )
    multi_use = fields.Boolean(
        description="Create Mediation for multiple use (default false)", required=False
    )


class ReceiveMediationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive Mediation request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (defaults to configuration)",
        required=False,
    )


class AcceptMediationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept Mediation request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)
    my_label = fields.Str(
        description="Label for connection", required=False, example="Broker"
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

    connection_id = fields.Str(
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
    tags=["mediation"],
    summary="Query mediation requests, returns all or filtered list by provided parameters.",
)
@querystring_schema(MediationsSchema())
@response_schema(MediationsListSchema(), 200)
async def list_mediations_records(request: web.BaseRequest):
    """
    Request handler for searching mediation records.

    Args:
        request: aiohttp request object

    Returns:
        The mediation list response

    """
    context = request.app["request_context"]
    # TODO: see of 'strict=True' in schema will do this for us.
    tag_filter = {}
    for param_name in (
        "mediation_id",
        "connection_id",
        "state"
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    post_filter = {} # TODO: find out what should be in positive negative filter
    try:
        records = await MediationRecord.query(context, tag_filter, post_filter)
        results = [record.serialize() for record in records]
        results.sort(key=mediation_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"results": results})


@docs(tags=["mediation"], summary="send and receive mediation request")
async def send_receive_mediations_request(request: web.BaseRequest):
    """
    Request handler for send/receive a mediation record.

    Args:
        request: aiohttp request object
    """


@docs(tags=["mediation"], summary="grant or deny mediation request")
async def grant_or_deny_mediations_request(request: web.BaseRequest):
    """
    Request handler for send/receive a mediation record.

    Args:
        request: aiohttp request object
    """


@docs(tags=["mediation"], summary="Remove an existing mediation record")
@match_info_schema(MediationIdSchema())
async def remove_mediations_record(request: web.BaseRequest):
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

async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/mediations", list_mediations_records, allow_head=False), # list records
            #web.connect("/mediations", send_mediator_request), # send request to other mediator
            web.post("/mediations", send_receive_mediations_request), # create mediations record
            web.put("/mediations", grant_or_deny_mediations_request), # update
            web.delete("/mediations", remove_mediations_record), # delete
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
