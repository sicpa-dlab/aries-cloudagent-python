"""Store state for Mediation requests."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....config.injection_context import InjectionContext

from .....messaging.models.base_record import BaseRecord, BaseRecordSchema

from .....storage.base import StorageNotFoundError, StorageDuplicateError


class MediationRecord(BaseRecord):
    """Class representing stored route information.

    Args:
        connection id:
        terms:
    """

    class Meta:
        """RouteRecord metadata."""

        schema_class = "MediationRecordSchema"

    RECORD_TYPE = "mediation_requests"
    RECORD_ID_NAME = "mediation_id"
    TAG_NAMES = {"state",  "role", "connection_id"}

    STATE_REQUEST_RECEIVED = "request_received"
    STATE_GRANTED = "granted"
    STATE_DENIED = "denied"

    ROLE_CLIENT = "client"
    ROLE_SERVER = "server"

    def __init__(
        self,
        *,
        mediation_id: str = None,
        state: str = None,
        role: str = None,
        connection_id: str = None,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None,
        recipient_keys: Sequence[str] = None,
        routing_keys: Sequence[str] = None,
        endpoint: str = None,
        **kwargs
    ):
        """
        Initialize a MediationRecord instance.

        Args:
            mediation_id:
            state:
            connection_id:
            terms:
        """
        super().__init__(
            mediation_id, state or self.STATE_REQUEST_RECEIVED, **kwargs
        )
        self.role = role if role else self.ROLE_SERVER
        self.connection_id = connection_id
        self.mediator_terms = list(mediator_terms) if mediator_terms else []
        self.recipient_terms = list(recipient_terms) if recipient_terms else []
        self.routing_keys = list(routing_keys) if routing_keys else []
        self.recipient_keys = list(recipient_keys) if recipient_keys else []
        self.endpoint = endpoint

    @property
    def mediation_id(self) -> str:
        """Get Mediation ID."""
        return self._id

    @property
    def state(self) -> str:
        """Get Mediation state."""
        return self._state

    @state.setter
    def state(self, state):
        """Setter for state."""
        if state not in [MediationRecord.STATE_DENIED,
                         MediationRecord.STATE_GRANTED,
                         MediationRecord.STATE_REQUEST_RECEIVED]:
            raise ValueError(
                f"{state} is not a valid state, "
                f"must be one of ("
                f"{MediationRecord.STATE_DENIED}, "
                f"{MediationRecord.STATE_GRANTED}, "
                f"{MediationRecord.STATE_REQUEST_RECEIVED}"
            )
        self._state = state

    @classmethod
    async def retrieve_by_connection_id(
        cls, context: InjectionContext, connection_id: str
    ):
        """Retrieve a route record by recipient key."""
        tag_filter = {"connection_id": connection_id}
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    @property
    def record_value(self) -> dict:
        """Accessor for JSON record value."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "connection_id",
                "state",
                "mediator_terms",
                "recipient_terms",
                "recipient_keys",
                "routing_keys",
                "endpoint",
            )
        }

    @classmethod
    async def exists_for_connection_id(
        cls, context: InjectionContext, connection_id: str
    ) -> bool:
        """Return whether a mediation record exists for the given connection."""
        tag_filter = {"connection_id": connection_id}
        try:
            record = await cls.retrieve_by_tag_filter(context, tag_filter)
        except StorageNotFoundError:
            return False
        except StorageDuplicateError:
            return True

        return bool(record)


class MediationRecordSchema(BaseRecordSchema):
    """MediationRecordSchema schema."""

    class Meta:
        """MediationRecordSchema metadata."""

        model_class = MediationRecord
        unknown = EXCLUDE

    mediation_id = fields.Str(required=False)
    role = fields.Str(required=True)
    endpoint = fields.Str(required=False)
    routing_keys = fields.List(fields.Str(), required=False)
    recipient_keys = fields.List(fields.Str(), required=False)
    connection_id = fields.Str(required=True)
    mediator_terms = fields.List(fields.Str(), required=False)
    recipient_terms = fields.List(fields.Str(), required=False)
