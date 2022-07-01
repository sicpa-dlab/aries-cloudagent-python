"""Wallet record."""
from typing import Any, Optional, Sequence
from marshmallow import fields
from marshmallow import validate
from marshmallow.utils import EXCLUDE
from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...messaging.valid import UUIDFour
from ..error import WalletSettingsError


class WalletRecord(BaseRecord):
    """Represents a wallet record."""

    class Meta:
        """WalletRecord metadata."""

        schema_class = "WalletRecordSchema"

    RECORD_TYPE = "wallet_record"
    RECORD_ID_NAME = "wallet_id"
    TAG_NAMES = {"wallet_name"}
    MODE_MANAGED = "managed"
    MODE_UNMANAGED = "unmanaged"

    def __init__(
        self,
        *,
        wallet_id: str = None,
        key_management_mode: str = None,
        settings: dict = None,
        wallet_name: str = None,
        jwt_iat: Optional[int] = None,
        **kwargs
    ):
        """Initialize a new WalletRecord."""
        super().__init__(wallet_id, **kwargs)
        self.key_management_mode = key_management_mode
        self.jwt_iat = jwt_iat
        self._settings = settings

    @property
    def wallet_id(self) -> str:
        """Accessor for the ID associated with this record."""
        return self._id

    @property
    def settings(self) -> dict:
        """Accessor for the context settings associated with this wallet."""
        return {**self._settings, "wallet.id": self.wallet_id}

    @property
    def wallet_name(self) -> Optional[str]:
        """Accessor for the name of the wallet."""
        return self.settings.get("wallet.name")

    @property
    def wallet_type(self) -> str:
        """Accessor for the type of the wallet."""
        return self.settings.get("wallet.type")

    @property
    def wallet_webhook_urls(self) -> Sequence[str]:
        """Accessor for webhook_urls of the wallet."""
        return self.settings.get("wallet.webhook_urls")

    @property
    def wallet_dispatch_type(self) -> str:
        """Accessor for webhook dispatch type of the wallet."""
        return self.settings.get("wallet.dispatch_type")

    @property
    def wallet_key(self) -> Optional[str]:
        """Accessor for the key of the wallet."""
        return self.settings.get("wallet.key")

    @property
    def wallet_key_derivation_method(self):
        """Accessor for the key derivation method of the wallet."""
        return self.settings.get("wallet.key_derivation_method")

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this record."""
        return {
            prop: getattr(self, prop)
            for prop in ("settings", "key_management_mode", "jwt_iat")
        }

    @property
    def is_managed(self) -> bool:
        """Accessor to check if the key management mode is managed."""
        return self.key_management_mode == WalletRecord.MODE_MANAGED

    @property
    def requires_external_key(self) -> bool:
        """Accessor to check if the wallet requires an external key."""
        if self.wallet_type == "in_memory":
            return False
        elif self.is_managed:
            return False
        else:
            return True

    def update_settings(self, settings: dict):
        """Update settings."""
        if "wallet.id" in settings:
            raise WalletSettingsError("wallet.id cannot be saved in settings.")
        self._settings.update(settings)

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class WalletRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of record."""

    class Meta:
        """WalletRecordSchema metadata."""

        model_class = WalletRecord
        unknown = EXCLUDE

    wallet_id = fields.Str(
        required=True,
        metadata={"description": "Wallet record ID", "example": UUIDFour.EXAMPLE},
    )
    key_management_mode = fields.Str(
        required=True,
        validate=validate.OneOf(
            [WalletRecord.MODE_MANAGED, WalletRecord.MODE_UNMANAGED]
        ),
        metadata={"description": "Mode regarding management of wallet key"},
    )
    settings = fields.Dict(
        required=False, metadata={"description": "Settings for this wallet."}
    )
