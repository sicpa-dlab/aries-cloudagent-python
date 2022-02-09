"""
Manage did and did document admin routes.

"""

from crypt import methods
from ssl import Options
from aiohttp import web
from aiohttp_apispec import (docs, match_info_schema, querystring_schema,
                             request_schema, response_schema)
from aries_cloudagent.messaging.models.openapi import OpenAPISchema
from marshmallow import fields

from ..admin.request_context import AdminRequestContext
from ..resolver.routes import (DIDMatchInfoSchema, ResolutionResultSchema,
                               _W3cDID)
from .base import DIDMethodNotSupported, DIDNotFound, RegistrarError
from .did_registrar import DIDRegistrar


class DIDRarMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking DID."""

    did = fields.Str(description="DID", required=False, **_W3cDID)
    method = fields.Str(description="DID method", required=False) # TODO: get validator 
    document = fields.Str(description="DID document", required=False) # TODO: get validator
    Options = fields.Str(description="DID creation options", required=False) # TODO: get validator

@docs(tags=["registrar"], summary="create and publish a did.")
@request_schema(DIDRarMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def create_did(request: web.Request):
    """Create a did."""
    context: AdminRequestContext = request["context"]
    body = await request.json()
    did = body.get("did")
    method = body.get("method","sov") # TODO: get default method from default
    document = body.get("document")
    options = body.get("options",{})
    try:
        session = await context.session()
        registrar = session.inject(DIDRegistrar)
        result = await registrar.create(context.profile, method, did, document)
    except DIDMethodNotSupported as err:
        raise web.HTTPNotImplemented(reason=err.roll_up) from err
    except RegistrarError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up) from err
    return web.json_response(result)


@docs(tags=["registrar"], summary="Update a did.")
@match_info_schema(DIDMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def update_did(request: web.Request):
    """Update a did."""
    context: AdminRequestContext = request["context"]

    did = request.match_info["did"]
    try:
        session = await context.session()
        registrar = session.inject(DIDRegistrar)
        result = await registrar.update(context.profile, did)
    except DIDNotFound as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except DIDMethodNotSupported as err:
        raise web.HTTPNotImplemented(reason=err.roll_up) from err
    except RegistrarError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up) from err
    return web.json_response(result)


@docs(tags=["registrar"], summary="Deactivate a did.")
@match_info_schema(DIDMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def deactivate_did(request: web.Request):
    """deactivate a did."""
    # you never quite the did club
    context: AdminRequestContext = request["context"]

    did = request.match_info["did"]
    try:
        session = await context.session()
        registrar = session.inject(DIDRegistrar)
        result = await registrar.deactivate(context.profile, did)
    except DIDNotFound as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except DIDMethodNotSupported as err:
        raise web.HTTPNotImplemented(reason=err.roll_up) from err
    except RegistrarError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up) from err
    return web.json_response(result)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/registrar/create", create_did),
            web.post("/registrar/update/{did}", update_did),
            web.post("/registrar/deactivate/{did}", deactivate_did),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "resolver",
            "description": "did resolver interface.",
            "externalDocs": {"description": "Specification"},  # , "url": SPEC_URI},
        }
    )
