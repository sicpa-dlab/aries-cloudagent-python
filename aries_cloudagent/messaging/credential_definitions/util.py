"""Credential definition utilities."""
import re
from marshmallow import fields
from ...core.profile import Profile
from ..models.openapi import OpenAPISchema
from ..valid import INDY_DID, INDY_CRED_DEF_ID, INDY_SCHEMA_ID, INDY_VERSION

CRED_DEF_SENT_RECORD_TYPE = "cred_def_sent"


class CredDefQueryStringSchema(OpenAPISchema):
    """Query string parameters for credential definition searches."""

    schema_id = fields.Str(
        required=False,
        metadata={"description": "Schema identifier", **INDY_SCHEMA_ID},
    )
    schema_issuer_did = fields.Str(
        required=False, metadata={"description": "Schema issuer DID", **INDY_DID}
    )
    schema_name = fields.Str(
        required=False, metadata={"description": "Schema name", "example": "membership"}
    )
    schema_version = fields.Str(
        required=False, metadata={"description": "Schema version", **INDY_VERSION}
    )
    issuer_did = fields.Str(
        required=False, metadata={"description": "Issuer DID", **INDY_DID}
    )
    cred_def_id = fields.Str(
        required=False,
        metadata={"description": "Credential definition id", **INDY_CRED_DEF_ID},
    )


CRED_DEF_TAGS = [
    tag for tag in vars(CredDefQueryStringSchema).get("_declared_fields", [])
]
CRED_DEF_EVENT_PREFIX = "acapy::CRED_DEF::"
EVENT_LISTENER_PATTERN = re.compile(f"^{CRED_DEF_EVENT_PREFIX}(.*)?$")


async def notify_cred_def_event(profile: Profile, cred_def_id: str, meta_data: dict):
    """Send notification for a cred def post-process event."""
    await profile.notify(CRED_DEF_EVENT_PREFIX + cred_def_id, meta_data)
