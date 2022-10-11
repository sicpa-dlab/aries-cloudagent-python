"""
Manage did and did document admin routes.

"""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    request_schema,
    response_schema,
)
from ..messaging.models.openapi import OpenAPISchema
from .models.job import JobRecord
from ..storage.error import StorageNotFoundError
from marshmallow import fields
from .registration_result import RegistrationResult

from ..admin.request_context import AdminRequestContext
from ..resolver.routes import DIDMatchInfoSchema, ResolutionResultSchema, _W3cDID
from .base import DIDMethodNotSupported, DIDNotFound, RegistrarError
from .did_registrars import DIDRegistrars


class DIDOptionMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking DID."""

    Options = fields.Str(
        description="DID creation options", required=False
    )  # TODO: get validator


class DIDCreateMatchInfoSchema(DIDOptionMatchInfoSchema):
    """Path parameters and validators for request creating DID."""

    did = fields.Str(description="DID", required=False, **_W3cDID)
    method = fields.Str(description="DID method", required=False)  # TODO: get validator
    document = fields.Dict(
        description="DID document", required=False
    )  # TODO: get validator


class DIDUpdateMatchInfoSchema(DIDOptionMatchInfoSchema):
    """Path parameters and validators for request taking DID."""

    document = fields.Dict(
        description="DID document", required=False
    )  # TODO: get validator


@docs(tags=["registrar"], summary="create and publish a did.")
@request_schema(DIDCreateMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def create_did(request: web.Request):
    """Create a did."""
    context: AdminRequestContext = request["context"]
    body = await request.json()
    did = body.get("did")
    method = body.get("method", "sov")  # TODO: get default method from default
    document = body.get("document")
    options = body.get("options", {})
    secret = {}  # TODO: support this
    try:
        session = await context.session()
        registrar = session.inject(DIDRegistrars)
        job_record: JobRecord = await registrar.create(
            context.profile,
            method,
            did,
            options,
            secret,
            document,
        )
        result = RegistrationResult(
            job_record.job_id, job_record.did_state
        )  # TODO; add meta data
    except DIDMethodNotSupported as err:
        raise web.HTTPNotImplemented(reason=err.roll_up) from err
    except RegistrarError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up) from err
    return web.json_response(result.serialize())


@docs(tags=["registrar"], summary="Update a did.")
@match_info_schema(DIDMatchInfoSchema())
@request_schema(DIDUpdateMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def update_did(request: web.Request):
    """Update a did."""
    context: AdminRequestContext = request["context"]
    body = await request.json()
    did = request.match_info["did"]
    document = body.get("document")
    options = body.get("options", {})
    secret = {}  # TODO: support this
    operation = []  # TODO: support this
    try:
        session = await context.session()
        registrar = session.inject(DIDRegistrars)
        job_record: JobRecord = await registrar.update(
            context.profile, did, options, secret, operation, document
        )
        result = RegistrationResult(
            job_record.job_id, job_record.did_state
        )  # TODO; add meta data
    except DIDNotFound as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except DIDMethodNotSupported as err:
        raise web.HTTPNotImplemented(reason=err.roll_up) from err
    except RegistrarError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up) from err
    return web.json_response(result.serialize())


@docs(tags=["registrar"], summary="Deactivate a did.")
@match_info_schema(DIDMatchInfoSchema())
@request_schema(DIDOptionMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def deactivate_did(request: web.Request):
    """deactivate a did."""
    # you never quit the did club
    context: AdminRequestContext = request["context"]
    did = request.match_info["did"]
    body = await request.json()
    options = body.get("options", {})
    secret = {}  # TODO: support this

    try:
        session = await context.session()
        registrar = session.inject(DIDRegistrars)
        job_record = await registrar.deactivate(context.profile, did, options, secret)
        result = RegistrationResult(
            job_record.job_id, job_record.did_state
        )  # TODO; add meta data
    except DIDNotFound as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except DIDMethodNotSupported as err:
        raise web.HTTPNotImplemented(reason=err.roll_up) from err
    except RegistrarError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up) from err
    return web.json_response(result.serialize())


@docs(tags=["registrar"], summary="did registration status.")
@match_info_schema(DIDMatchInfoSchema())
@response_schema(ResolutionResultSchema(), 200)
async def status_job(request: web.Request):
    """Check status of requested did"""
    context: AdminRequestContext = request["context"]
    did = request.match_info["did"]

    try:
        session = await context.session()
        job_record = await JobRecord.retrieve_by_did(session, did)
        result = RegistrationResult(
            job_record.job_id, job_record.did_state
        )  # TODO; add meta data

    except StorageNotFoundError as err:  # TODO: update to include other errors
        raise web.HTTPNotFound(reason=err.roll_up) from err
    return web.json_response(result.serialize)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/registrar/create", create_did),
            web.post("/registrar/update/{did}", update_did),
            web.post("/registrar/deactivate/{did}", deactivate_did),
            web.post("/registrar/status/{did}", status_job),
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
