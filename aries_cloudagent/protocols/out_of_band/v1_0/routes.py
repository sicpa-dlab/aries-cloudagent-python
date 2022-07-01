"""Out-of-band handling admin routes."""
import json
import logging

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema
from marshmallow import fields, validate
from marshmallow.exceptions import ValidationError

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecordSchema
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4
from ....storage.error import StorageError, StorageNotFoundError
from ...didcomm_prefix import DIDCommPrefix
from ...didexchange.v1_0.manager import DIDXManagerError
from .manager import OutOfBandManager, OutOfBandManagerError
from .message_types import SPEC_URI
from .messages.invitation import HSProto, InvitationMessage, InvitationMessageSchema
from .models.invitation import InvitationRecordSchema

LOGGER = logging.getLogger(__name__)


class OutOfBandModuleResponseSchema(OpenAPISchema):
    """Response schema for Out of Band Module."""


class InvitationCreateQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create invitation request query string."""

    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    multi_use = fields.Boolean(
        required=False,
        metadata={"description": "Create invitation for multiple use (default false)"},
    )


class InvitationCreateRequestSchema(OpenAPISchema):
    """Invitation create request Schema."""

    class AttachmentDefSchema(OpenAPISchema):
        """Attachment Schema."""

        _id = fields.Str(
            data_key="id",
            metadata={
                "description": "Attachment identifier",
                "example": "attachment-0",
            },
        )
        _type = fields.Str(
            data_key="type",
            validate=validate.OneOf(["credential-offer", "present-proof"]),
            metadata={"description": "Attachment type", "example": "present-proof"},
        )

    attachments = fields.Nested(
        AttachmentDefSchema,
        required=False,
        metadata={"many": True, "description": "Optional invitation attachments"},
    )
    handshake_protocols = fields.List(
        fields.Str(
            description="Handshake protocol to specify in invitation",
            example=DIDCommPrefix.qualify_current(HSProto.RFC23.name),
            validate=lambda hsp: HSProto.get(hsp) is not None,
        ),
        required=False,
    )
    use_public_did = fields.Boolean(
        dump_default=False,
        metadata={
            "description": "Whether to use public DID in invitation",
            "example": False,
        },
    )
    metadata = fields.Dict(
        required=False,
        metadata={
            "description": "Optional metadata to attach to the connection created with the invitation"
        },
    )
    my_label = fields.Str(
        required=False,
        metadata={
            "description": "Label for connection invitation",
            "example": "Invitation to Barry",
        },
    )
    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    mediation_id = fields.Str(
        required=False,
        metadata={
            "description": "Identifier for active mediation record to be used",
            **UUID4,
        },
    )


class InvitationReceiveQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive invitation request query string."""

    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    use_existing_connection = fields.Boolean(
        required=False,
        dump_default=True,
        metadata={"description": "Use an existing connection, if possible"},
    )
    mediation_id = fields.Str(
        required=False,
        metadata={
            "description": "Identifier for active mediation record to be used",
            **UUID4,
        },
    )


@docs(tags=["out-of-band"], summary="Create a new connection invitation")
@querystring_schema(InvitationCreateQueryStringSchema())
@request_schema(InvitationCreateRequestSchema())
@response_schema(InvitationRecordSchema(), description="")
async def invitation_create(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """
    context: AdminRequestContext = request["context"]
    body = await request.json() if request.body_exists else {}
    attachments = body.get("attachments")
    handshake_protocols = body.get("handshake_protocols", [])
    use_public_did = body.get("use_public_did", False)
    metadata = body.get("metadata")
    my_label = body.get("my_label")
    alias = body.get("alias")
    mediation_id = body.get("mediation_id")
    multi_use = json.loads(request.query.get("multi_use", "false"))
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    profile = context.profile
    oob_mgr = OutOfBandManager(profile)
    try:
        invi_rec = await oob_mgr.create_invitation(
            my_label=my_label,
            auto_accept=auto_accept,
            public=use_public_did,
            hs_protos=[
                h for h in [HSProto.get(hsp) for hsp in handshake_protocols] if h
            ],
            multi_use=multi_use,
            attachments=attachments,
            metadata=metadata,
            alias=alias,
            mediation_id=mediation_id,
        )
    except (StorageNotFoundError, ValidationError, OutOfBandManagerError) as e:
        raise web.HTTPBadRequest(reason=e.roll_up)
    return web.json_response(invi_rec.serialize())


@docs(tags=["out-of-band"], summary="Receive a new connection invitation")
@querystring_schema(InvitationReceiveQueryStringSchema())
@request_schema(InvitationMessageSchema())
@response_schema(ConnRecordSchema(), 200, description="")
async def invitation_receive(request: web.BaseRequest):
    """
    Request handler for receiving a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """
    context: AdminRequestContext = request["context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of invitations"
        )
    profile = context.profile
    oob_mgr = OutOfBandManager(profile)
    body = await request.json()
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    alias = request.query.get("alias")
    use_existing_conn = json.loads(request.query.get("use_existing_connection", "true"))
    mediation_id = request.query.get("mediation_id")
    try:
        invitation = InvitationMessage.deserialize(body)
        result = await oob_mgr.receive_invitation(
            invitation,
            auto_accept=auto_accept,
            alias=alias,
            use_existing_connection=use_existing_conn,
            mediation_id=mediation_id,
        )
    except (DIDXManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(result.serialize())


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/out-of-band/create-invitation", invitation_create),
            web.post("/out-of-band/receive-invitation", invitation_receive),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "out-of-band",
            "description": "Out-of-band connections",
            "externalDocs": {"description": "Design", "url": SPEC_URI},
        }
    )
