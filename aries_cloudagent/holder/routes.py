"""Holder admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields

from ..admin.request_context import AdminRequestContext
from ..indy.holder import IndyHolder, IndyHolderError
from ..indy.models.cred_precis import IndyCredInfoSchema
from ..ledger.base import BaseLedger
from ..ledger.error import LedgerError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    Endpoint,
    IndyWQL,
    NumericStrNatural,
    NumericStrWhole,
    UUIDFour,
)
from ..storage.error import StorageError, StorageNotFoundError
from ..storage.vc_holder.base import VCHolder
from ..storage.vc_holder.vc_record import VCRecordSchema
from ..wallet.error import WalletNotFoundError


class HolderModuleResponseSchema(OpenAPISchema):
    """Response schema for Holder Module."""


class AttributeMimeTypesResultSchema(OpenAPISchema):
    """Result schema for credential attribute MIME type."""

    results = fields.Dict(
        keys=fields.Str(metadata={"description": "Attribute name"}),
        values=fields.Str(metadata={"description": "MIME type"}),
        allow_none=True,
    )


class CredInfoListSchema(OpenAPISchema):
    """Result schema for credential query."""

    results = fields.List(fields.Nested(IndyCredInfoSchema()))


class CredentialsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in credentials list query."""

    start = fields.Str(
        required=False,
        validate=NumericStrWhole(),
        metadata={"description": "Start index", "example": NumericStrWhole.EXAMPLE},
    )
    count = fields.Str(
        required=False,
        validate=NumericStrNatural(),
        metadata={
            "description": "Maximum number to retrieve",
            "example": NumericStrNatural.EXAMPLE,
        },
    )
    wql = fields.Str(
        required=False,
        validate=IndyWQL(),
        metadata={"description": "(JSON) WQL query", "example": IndyWQL.EXAMPLE},
    )


class W3CCredentialsListRequestSchema(OpenAPISchema):
    """Parameters and validators for W3C credentials request."""

    contexts = fields.List(
        fields.Str(
            validate=Endpoint(),
            metadata={
                "description": "Credential context to match",
                "example": Endpoint.EXAMPLE,
            },
        ),
        required=False,
    )
    types = fields.List(
        fields.Str(
            validate=Endpoint(),
            metadata={
                "description": "Credential type to match",
                "example": Endpoint.EXAMPLE,
            },
        ),
        required=False,
    )
    schema_ids = fields.List(
        fields.Str(
            validate=Endpoint(),
            metadata={
                "description": "Credential schema identifier",
                "example": Endpoint.EXAMPLE,
            },
        ),
        required=False,
        metadata={"description": "Schema identifiers, all of which to match"},
    )
    issuer_id = fields.Str(
        required=False,
        metadata={"description": "Credential issuer identifier to match"},
    )
    subject_ids = fields.List(
        fields.Str(metadata={"description": "Subject identifier"}),
        required=False,
        metadata={"description": "Subject identifiers, all of which to match"},
    )
    proof_types = fields.List(
        fields.Str(
            metadata={
                "description": "Signature suite used for proof",
                "example": "Ed25519Signature2018",
            }
        )
    )
    given_id = fields.Str(
        required=False, metadata={"description": "Given credential id to match"}
    )
    tag_query = fields.Dict(
        keys=fields.Str(metadata={"description": "Tag name"}),
        values=fields.Str(metadata={"description": "Tag value"}),
        required=False,
        metadata={"description": "Tag filter"},
    )
    max_results = fields.Int(
        required=False,
        metadata={"strict": True, "description": "Maximum number of results to return"},
    )


class VCRecordListSchema(OpenAPISchema):
    """Result schema for W3C credential query."""

    results = fields.List(fields.Nested(VCRecordSchema()))


class HolderCredIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    credential_id = fields.Str(
        required=True,
        metadata={"description": "Credential identifier", "example": UUIDFour.EXAMPLE},
    )


class CredRevokedQueryStringSchema(OpenAPISchema):
    """Path parameters and validators for request seeking cred revocation status."""

    fro = fields.Str(
        data_key="from",
        required=False,
        validate=NumericStrWhole(),
        metadata={
            "description": "Earliest epoch of revocation status interval of interest",
            "example": NumericStrWhole.EXAMPLE,
        },
    )
    to = fields.Str(
        required=False,
        validate=NumericStrWhole(),
        metadata={
            "description": "Latest epoch of revocation status interval of interest",
            "example": NumericStrWhole.EXAMPLE,
        },
    )


class CredRevokedResultSchema(OpenAPISchema):
    """Result schema for credential revoked request."""

    revoked = fields.Bool(
        metadata={"description": "Whether credential is revoked on the ledger"}
    )


@docs(tags=["credentials"], summary="Fetch credential from wallet by id")
@match_info_schema(HolderCredIdMatchInfoSchema())
@response_schema(IndyCredInfoSchema(), 200, description="")
async def credentials_get(request: web.BaseRequest):
    """
    Request handler for retrieving credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential info

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    holder = context.profile.inject(IndyHolder)
    try:
        credential = await holder.get_credential(credential_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    credential_json = json.loads(credential)
    return web.json_response(credential_json)


@docs(tags=["credentials"], summary="Query credential revocation status by id")
@match_info_schema(HolderCredIdMatchInfoSchema())
@querystring_schema(CredRevokedQueryStringSchema())
@response_schema(CredRevokedResultSchema(), 200, description="")
async def credentials_revoked(request: web.BaseRequest):
    """
    Request handler for querying revocation status of credential.

    Args:
        request: aiohttp request object

    Returns:
        Empty production

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]
    fro = request.query.get("from")
    to = request.query.get("to")

    async with context.profile.session() as session:
        ledger = session.inject_or(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not context.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

        async with ledger:
            try:
                holder = session.inject(IndyHolder)
                revoked = await holder.credential_revoked(
                    ledger,
                    credential_id,
                    int(fro) if fro else None,
                    int(to) if to else None,
                )
            except WalletNotFoundError as err:
                raise web.HTTPNotFound(reason=err.roll_up) from err
            except LedgerError as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"revoked": revoked})


@docs(tags=["credentials"], summary="Get attribute MIME types from wallet")
@match_info_schema(HolderCredIdMatchInfoSchema())
@response_schema(AttributeMimeTypesResultSchema(), 200, description="")
async def credentials_attr_mime_types_get(request: web.BaseRequest):
    """
    Request handler for getting credential attribute MIME types.

    Args:
        request: aiohttp request object

    Returns:
        The MIME types response

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    async with context.profile.session() as session:
        holder = session.inject(IndyHolder)
        mime_types = await holder.get_mime_type(credential_id)
    return web.json_response({"results": mime_types})


@docs(tags=["credentials"], summary="Remove credential from wallet by id")
@match_info_schema(HolderCredIdMatchInfoSchema())
@response_schema(HolderModuleResponseSchema(), description="")
async def credentials_remove(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        Empty production

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    try:
        async with context.profile.session() as session:
            holder = session.inject(IndyHolder)
            await holder.delete_credential(credential_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({})


@docs(
    tags=["credentials"],
    summary="Fetch credentials from wallet",
)
@querystring_schema(CredentialsListQueryStringSchema())
@response_schema(CredInfoListSchema(), 200, description="")
async def credentials_list(request: web.BaseRequest):
    """
    Request handler for searching credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential info list response

    """
    context: AdminRequestContext = request["context"]
    start = request.query.get("start")
    count = request.query.get("count")

    # url encoded json wql
    encoded_wql = request.query.get("wql") or "{}"
    wql = json.loads(encoded_wql)

    # defaults
    start = int(start) if isinstance(start, str) else 0
    count = int(count) if isinstance(count, str) else 10

    async with context.profile.session() as session:
        holder = session.inject(IndyHolder)
        try:
            credentials = await holder.get_credentials(start, count, wql)
        except IndyHolderError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": credentials})


@docs(
    tags=["credentials"],
    summary="Fetch W3C credential from wallet by id",
)
@match_info_schema(HolderCredIdMatchInfoSchema())
@response_schema(VCRecordSchema(), 200, description="")
async def w3c_cred_get(request: web.BaseRequest):
    """
    Request handler for retrieving W3C credential.

    Args:
        request: aiohttp request object

    Returns:
        Verifiable credential record

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    async with context.profile.session() as session:
        holder = session.inject(VCHolder)
        try:
            vc_record = await holder.retrieve_credential_by_id(credential_id)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(vc_record.serialize())


@docs(
    tags=["credentials"],
    summary="Remove W3C credential from wallet by id",
)
@match_info_schema(HolderCredIdMatchInfoSchema())
@response_schema(HolderModuleResponseSchema(), 200, description="")
async def w3c_cred_remove(request: web.BaseRequest):
    """
    Request handler for deleting W3C credential.

    Args:
        request: aiohttp request object

    Returns:
        Empty production

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    async with context.profile.session() as session:
        holder = session.inject(VCHolder)
        try:
            vc_record = await holder.retrieve_credential_by_id(credential_id)
            await holder.delete_credential(vc_record)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(
    tags=["credentials"],
    summary="Fetch W3C credentials from wallet",
)
@request_schema(W3CCredentialsListRequestSchema())
@querystring_schema(CredentialsListQueryStringSchema())
@response_schema(VCRecordListSchema(), 200, description="")
async def w3c_creds_list(request: web.BaseRequest):
    """
    Request handler for searching W3C credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential record list response

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    contexts = body.get("contexts")
    types = body.get("types")
    schema_ids = body.get("schema_ids")
    issuer_id = body.get("issuer_id")
    subject_ids = body.get("subject_ids")
    proof_types = body.get("proof_types")
    given_id = body.get("given_id")
    tag_query = body.get("tag_query")
    max_results = body.get("max_results")

    async with context.profile.session() as session:
        holder = session.inject(VCHolder)
        try:
            search = holder.search_credentials(
                contexts=contexts,
                types=types,
                schema_ids=schema_ids,
                issuer_id=issuer_id,
                subject_ids=subject_ids,
                proof_types=proof_types,
                given_id=given_id,
                tag_query=tag_query,
            )
            records = await search.fetch(max_results)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": [record.serialize() for record in records]})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/credential/{credential_id}", credentials_get, allow_head=False),
            web.get(
                "/credential/revoked/{credential_id}",
                credentials_revoked,
                allow_head=False,
            ),
            web.get(
                "/credential/mime-types/{credential_id}",
                credentials_attr_mime_types_get,
                allow_head=False,
            ),
            web.delete("/credential/{credential_id}", credentials_remove),
            web.get("/credentials", credentials_list, allow_head=False),
            web.get(
                "/credential/w3c/{credential_id}",
                w3c_cred_get,
                allow_head=False,
            ),
            web.delete("/credential/w3c/{credential_id}", w3c_cred_remove),
            web.post("/credentials/w3c", w3c_creds_list),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "credentials",
            "description": "Holder credential management",
            "externalDocs": {
                "description": "Overview",
                "url": "https://w3c.github.io/vc-data-model/#credentials",
            },
        }
    )
