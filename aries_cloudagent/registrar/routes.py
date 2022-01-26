"""
Manage did and did document admin routes.

"""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, response_schema

from ..admin.request_context import AdminRequestContext
from ..resolver.routes import DIDMatchInfoSchema, ResolutionResultSchema
from .base import DIDMethodNotSupported, DIDNotFound, RegistrarError
from .did_registrar import DIDRegistrar


@docs(tags=["registrar"], summary="create and publish a did.")
@match_info_schema(DIDMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def create_did(request: web.Request):
    """Create a did."""
    context: AdminRequestContext = request["context"]

    did = request.match_info["did"]
    try:
        session = await context.session()
        registrar = session.inject(DIDRegistrar)
        result = await registrar.create(context.profile, did)
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
            web.post("/registrar/create/{method}", create_did, allow_head=False),
            web.post("/registrar/update/{did}", update_did, allow_head=False),
            web.post("/registrar/deactivate/{did}", deactivate_did, allow_head=False),
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
