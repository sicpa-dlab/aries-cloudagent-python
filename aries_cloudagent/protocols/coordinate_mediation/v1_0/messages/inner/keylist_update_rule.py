"""Inner structure of keylist-update message.

Represents single item of keylist-update.updates.
"""


from marshmallow import fields
from marshmallow.validate import OneOf

from ......messaging.models.base import BaseModel, BaseModelSchema
from ......messaging.valid import IndyRawPublicKey


class KeylistUpdateRule(BaseModel):
    """Class representing a keylist update rule."""

    class Meta:
        """Keylist update metadata."""

        schema_class = "KeylistUpdateRuleSchema"

    RULE_ADD = "add"
    RULE_REMOVE = "remove"

    def __init__(self, recipient_key: str, action: str, **kwargs):
        """
        Initialize keylist update rule object.

        Args:
            recipient_key: recipient key for the rule
            action: action for the rule

        """
        super().__init__(**kwargs)
        self.recipient_key = recipient_key
        self.action = action


class KeylistUpdateRuleSchema(BaseModelSchema):
    """Keylist update specification schema."""

    class Meta:
        """Keylist update schema metadata."""

        model_class = KeylistUpdateRule

    recipient_key = fields.Str(
        required=True,
        validate=IndyRawPublicKey(),
        metadata={
            "description": "Key to remove or add",
            "example": IndyRawPublicKey.EXAMPLE,
        },
    )
    action = fields.Str(
        required=True,
        validate=OneOf(["add", "remove"]),
        metadata={
            "description": "Action for specific key",
            "example": KeylistUpdateRule.RULE_ADD,
        },
    )
