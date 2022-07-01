"""Admin routes for presentations."""
from typing import Mapping
from marshmallow import EXCLUDE, fields
from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_CRED_REV_ID,
    INDY_REV_REG_ID,
    INDY_SCHEMA_ID,
    UUIDFour,
)
from .non_rev_interval import IndyNonRevocationIntervalSchema


class IndyCredInfo(BaseModel):
    """Indy cred info, as holder gets via indy-sdk."""

    class Meta:
        """IndyCredInfo metadata."""

        schema_class = "IndyCredInfoSchema"

    def __init__(
        self,
        referent: str = None,
        attrs: Mapping = None,
        schema_id: str = None,
        cred_def_id: str = None,
        rev_reg_id: str = None,
        cred_rev_id: str = None,
    ):
        """Initialize indy cred info."""
        self.referent = referent
        self.attrs = attrs
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id


class IndyCredInfoSchema(BaseModelSchema):
    """Schema for indy cred-info."""

    class Meta:
        """Schema metadata."""

        model_class = IndyCredInfo
        unknown = EXCLUDE

    referent = fields.Str(
        metadata={"description": "Wallet referent", "example": UUIDFour.EXAMPLE}
    )
    attrs = fields.Dict(
        metadata={
            "description": "Attribute names and value",
            "keys": fields.Str(example="userid"),
            "values": fields.Str(example="alice"),
        }
    )
    schema_id = fields.Str(
        metadata={"description": "Schema identifier", **INDY_SCHEMA_ID}
    )
    cred_def_id = fields.Str(
        metadata={
            "description": "Credential definition identifier",
            **INDY_CRED_DEF_ID,
        }
    )
    rev_reg_id = fields.Str(
        allow_none=True,
        metadata={
            "description": "Revocation registry identifier",
            **INDY_REV_REG_ID,
        },
    )
    cred_rev_id = fields.Str(
        allow_none=True,
        metadata={
            "description": "Credential revocation identifier",
            **INDY_CRED_REV_ID,
        },
    )


class IndyCredPrecisSchema(OpenAPISchema):
    """Schema for precis that indy credential search returns (and aca-py augments)."""

    cred_info = fields.Nested(
        IndyCredInfoSchema(), metadata={"description": "Credential info"}
    )
    interval = fields.Nested(
        IndyNonRevocationIntervalSchema(),
        metadata={"description": "Non-revocation interval from presentation request"},
    )
    presentation_referents = fields.List(
        fields.Str(description="presentation referent", example="1_age_uuid")
    )
