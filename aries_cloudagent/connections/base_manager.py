"""
Class to provide some common utilities.

For Connection, DIDExchange and OutOfBand Manager.
"""

import logging
from typing import List, Optional, Sequence, Text, Tuple, Union

from multiformats import multibase, multicodec
from pydid import (
    BaseDIDDocument as ResolvedDocument,
    DIDCommService,
    VerificationMethod,
)
import pydid
from pydid.verification_method import (
    Ed25519VerificationKey2018,
    Ed25519VerificationKey2020,
    JsonWebKey2020,
)

from ..config.logging import get_logger_inst
from ..core.error import BaseError
from ..core.profile import Profile
from ..did.did_key import DIDKey
from ..protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)
from ..protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from ..protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ..protocols.out_of_band.v1_0.messages.invitation import InvitationMessage
from ..resolver.base import ResolverError
from ..resolver.did_resolver import DIDResolver
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..wallet.base import BaseWallet
from ..wallet.did_info import DIDInfo
from ..wallet.util import b64_to_bytes, bytes_to_b58
from .models.conn_record import ConnRecord
from .models.connection_target import ConnectionTarget
from .models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service


class BaseConnectionManagerError(BaseError):
    """BaseConnectionManager error."""


class BaseConnectionManager:
    """Class to provide utilities regarding connection_targets."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, profile: Profile):
        """
        Initialize a BaseConnectionManager.

        Args:
            session: The profile session for this presentation
        """
        self._profile = profile
        self._route_manager = profile.inject(RouteManager)
        self._logger: logging.Logger = get_logger_inst(
            profile=self._profile,
            logger_name=__name__,
        )

    async def create_did_document(
        self,
        did_info: DIDInfo,
        inbound_connection_id: str = None,
        svc_endpoints: Sequence[str] = None,
        mediation_records: List[MediationRecord] = None,
    ) -> DIDDoc:
        """Create our DID doc for a given DID.

        Args:
            did_info: The DID information (DID and verkey) used in the connection
            inbound_connection_id: The ID of the inbound routing connection to use
            svc_endpoints: Custom endpoints for the DID Document
            mediation_record: The record for mediation that contains routing_keys and
                service endpoint

        Returns:
            The prepared `DIDDoc` instance

        """

        did_doc = DIDDoc(did=did_info.did)
        did_controller = did_info.did
        did_key = did_info.verkey
        pk = PublicKey(
            did_info.did,
            "1",
            did_key,
            PublicKeyType.ED25519_SIG_2018,
            did_controller,
            True,
        )
        did_doc.set(pk)

        router_id = inbound_connection_id
        routing_keys = []
        router_idx = 1
        while router_id:
            # look up routing connection information
            async with self._profile.session() as session:
                router = await ConnRecord.retrieve_by_id(session, router_id)
            if ConnRecord.State.get(router.state) != ConnRecord.State.COMPLETED:
                raise BaseConnectionManagerError(
                    f"Router connection not completed: {router_id}"
                )
            routing_doc, _ = await self.fetch_did_document(router.their_did)
            if not routing_doc.service:
                raise BaseConnectionManagerError(
                    f"No services defined by routing DIDDoc: {router_id}"
                )
            for service in routing_doc.service.values():
                if not service.endpoint:
                    raise BaseConnectionManagerError(
                        "Routing DIDDoc service has no service endpoint"
                    )
                if not service.recip_keys:
                    raise BaseConnectionManagerError(
                        "Routing DIDDoc service has no recipient key(s)"
                    )
                rk = PublicKey(
                    did_info.did,
                    f"routing-{router_idx}",
                    service.recip_keys[0].value,
                    PublicKeyType.ED25519_SIG_2018,
                    did_controller,
                    True,
                )
                routing_keys.append(rk)
                svc_endpoints = [service.endpoint]
                break
            router_id = router.inbound_connection_id

        if mediation_records:
            for mediation_record in mediation_records:
                mediator_routing_keys = [
                    PublicKey(
                        did_info.did,
                        f"routing-{idx}",
                        key,
                        PublicKeyType.ED25519_SIG_2018,
                        did_controller,  # TODO: get correct controller did_info
                        True,  # TODO: should this be true?
                    )
                    for idx, key in enumerate(mediation_record.routing_keys)
                ]

                routing_keys = [*routing_keys, *mediator_routing_keys]
                svc_endpoints = [mediation_record.endpoint]

        for endpoint_index, svc_endpoint in enumerate(svc_endpoints or []):
            endpoint_ident = "indy" if endpoint_index == 0 else f"indy{endpoint_index}"
            service = Service(
                did_info.did,
                endpoint_ident,
                "IndyAgent",
                [pk],
                routing_keys,
                svc_endpoint,
            )
            did_doc.set(service)

        return did_doc

    async def store_did_document(self, did_doc: DIDDoc):
        """Store a DID document.

        Args:
            did_doc: The `DIDDoc` instance to persist
        """
        assert did_doc.did

        try:
            stored_doc, record = await self.fetch_did_document(did_doc.did)
        except StorageNotFoundError:
            record = StorageRecord(
                self.RECORD_TYPE_DID_DOC,
                did_doc.to_json(),
                {"did": did_doc.did},
            )
            async with self._profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.add_record(record)
        else:
            async with self._profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.update_record(
                    record, did_doc.to_json(), {"did": did_doc.did}
                )
        await self.remove_keys_for_did(did_doc.did)
        for key in did_doc.pubkey.values():
            if key.controller == did_doc.did:
                await self.add_key_for_did(did_doc.did, key.value)

    async def add_key_for_did(self, did: str, key: str):
        """Store a verkey for lookup against a DID.

        Args:
            did: The DID to associate with this key
            key: The verkey to be added
        """
        record = StorageRecord(self.RECORD_TYPE_DID_KEY, key, {"did": did, "key": key})
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            await storage.add_record(record)

    async def find_did_for_key(self, key: str) -> str:
        """Find the DID previously associated with a key.

        Args:
            key: The verkey to look up
        """
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            record = await storage.find_record(self.RECORD_TYPE_DID_KEY, {"key": key})
        return record.tags["did"]

    async def remove_keys_for_did(self, did: str):
        """Remove all keys associated with a DID.

        Args:
            did: The DID for which to remove keys
        """
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            await storage.delete_all_records(self.RECORD_TYPE_DID_KEY, {"did": did})

    async def resolve_didcomm_services(
        self, did: str, service_accept: Optional[Sequence[Text]] = None
    ) -> Tuple[ResolvedDocument, List[DIDCommService]]:
        """Resolve a DIDComm services for a given DID."""
        if not did.startswith("did:"):
            # DID is bare indy "nym"
            # prefix with did:sov: for backwards compatibility
            did = f"did:sov:{did}"

        resolver = self._profile.inject(DIDResolver)
        try:
            doc_dict: dict = await resolver.resolve(self._profile, did, service_accept)
            doc: ResolvedDocument = pydid.deserialize_document(doc_dict, strict=True)
        except ResolverError as error:
            raise BaseConnectionManagerError(
                "Failed to resolve public DID in invitation"
            ) from error

        if not doc.service:
            raise BaseConnectionManagerError(
                "Cannot connect via public DID that has no associated services"
            )

        didcomm_services = sorted(
            [service for service in doc.service if isinstance(service, DIDCommService)],
            key=lambda service: service.priority,
        )

        return doc, didcomm_services

    async def verification_methods_for_service(
        self, doc: ResolvedDocument, service: DIDCommService
    ) -> Tuple[List[VerificationMethod], List[VerificationMethod]]:
        """Dereference recipient and routing keys.

        Returns verification methods for a DIDComm service to enable extracting
        key material.
        """
        resolver = self._profile.inject(DIDResolver)
        recipient_keys: List[VerificationMethod] = [
            await resolver.dereference_verification_method(
                self._profile, url, document=doc
            )
            for url in service.recipient_keys
        ]
        routing_keys: List[VerificationMethod] = [
            await resolver.dereference_verification_method(
                self._profile, url, document=doc
            )
            for url in service.routing_keys
        ]
        return recipient_keys, routing_keys

    async def resolve_invitation(
        self, did: str, service_accept: Optional[Sequence[Text]] = None
    ) -> Tuple[str, List[str], List[str]]:
        """
        Resolve invitation with the DID Resolver.

        Args:
            did: Document ID to resolve
        """
        doc, didcomm_services = await self.resolve_didcomm_services(did, service_accept)
        if not didcomm_services:
            raise BaseConnectionManagerError(
                "Cannot connect via public DID that has no associated DIDComm services"
            )

        first_didcomm_service, *_ = didcomm_services

        endpoint = str(first_didcomm_service.service_endpoint)
        recipient_keys, routing_keys = await self.verification_methods_for_service(
            doc, first_didcomm_service
        )

        return (
            endpoint,
            [
                self._extract_key_material_in_base58_format(key)
                for key in recipient_keys
            ],
            [self._extract_key_material_in_base58_format(key) for key in routing_keys],
        )

    async def record_keys_for_public_did(self, did: str):
        """Record the keys for a public DID.

        This is required to correlate sender verkeys back to a connection.
        """
        doc, didcomm_services = await self.resolve_didcomm_services(did)
        for service in didcomm_services:
            recips, _ = await self.verification_methods_for_service(doc, service)
            for recip in recips:
                await self.add_key_for_did(
                    did, self._extract_key_material_in_base58_format(recip)
                )

    async def resolve_connection_targets(
        self,
        did: str,
        sender_verkey: Optional[str] = None,
        their_label: Optional[str] = None,
    ) -> List[ConnectionTarget]:
        """Resolve connection targets for a DID."""
        self._logger.debug("Resolving connection targets for DID %s", did)
        doc, didcomm_services = await self.resolve_didcomm_services(did)
        self._logger.debug("Resolved DID document: %s", doc)
        self._logger.debug("Resolved DIDComm services: %s", didcomm_services)
        targets = []
        for service in didcomm_services:
            try:
                recips, routing = await self.verification_methods_for_service(
                    doc, service
                )
                endpoint = str(service.service_endpoint)
                targets.append(
                    ConnectionTarget(
                        did=doc.id,
                        endpoint=endpoint,
                        label=their_label,
                        recipient_keys=[
                            self._extract_key_material_in_base58_format(key)
                            for key in recips
                        ],
                        routing_keys=[
                            self._extract_key_material_in_base58_format(key)
                            for key in routing
                        ],
                        sender_key=sender_verkey,
                    )
                )
            except ResolverError:
                self._logger.exception(
                    "Failed to resolve service details while determining "
                    "connection targets; skipping service"
                )
                continue

        return targets

    @staticmethod
    def _extract_key_material_in_base58_format(method: VerificationMethod) -> str:
        if isinstance(method, Ed25519VerificationKey2018):
            return method.material
        elif isinstance(method, Ed25519VerificationKey2020):
            raw_data = multibase.decode(method.material)
            if len(raw_data) == 32:  # No multicodec prefix
                return bytes_to_b58(raw_data)
            else:
                codec, key = multicodec.unwrap(raw_data)
                if codec == multicodec.multicodec("ed25519-pub"):
                    return bytes_to_b58(key)
                else:
                    raise BaseConnectionManagerError(
                        f"Key type {type(method).__name__} "
                        f"with multicodec value {codec} is not supported"
                    )

        elif isinstance(method, JsonWebKey2020):
            if method.public_key_jwk.get("kty") == "OKP":
                return bytes_to_b58(b64_to_bytes(method.public_key_jwk.get("x"), True))
            else:
                raise BaseConnectionManagerError(
                    f"Key type {type(method).__name__} "
                    f"with kty {method.public_key_jwk.get('kty')} is not supported"
                )
        else:
            raise BaseConnectionManagerError(
                f"Key type {type(method).__name__} is not supported"
            )

    async def _fetch_connection_targets_for_invitation(
        self,
        connection: ConnRecord,
        invitation: Union[ConnectionInvitation, InvitationMessage],
        sender_verkey: str,
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets for an invitation.

        This will extract target info for either a connection or OOB invitation.

        Args:
            connection: ConnRecord the invitation is associated with.
            invitation: Connection or OOB invitation retrieved from conn record.

        Returns:
            A list of `ConnectionTarget` objects
        """
        if isinstance(invitation, ConnectionInvitation):
            # conn protocol invitation
            if invitation.did:
                did = invitation.did
                (
                    endpoint,
                    recipient_keys,
                    routing_keys,
                ) = await self.resolve_invitation(did)

            else:
                endpoint = invitation.endpoint
                recipient_keys = invitation.recipient_keys
                routing_keys = invitation.routing_keys
        else:
            # out-of-band invitation
            oob_service_item = invitation.services[0]
            if isinstance(oob_service_item, str):
                (
                    endpoint,
                    recipient_keys,
                    routing_keys,
                ) = await self.resolve_invitation(oob_service_item)

            else:
                endpoint = oob_service_item.service_endpoint
                recipient_keys = [
                    DIDKey.from_did(k).public_key_b58
                    for k in oob_service_item.recipient_keys
                ]
                routing_keys = [
                    DIDKey.from_did(k).public_key_b58
                    for k in oob_service_item.routing_keys
                ]

        return [
            ConnectionTarget(
                did=connection.their_did,
                endpoint=endpoint,
                label=invitation.label if invitation else None,
                recipient_keys=recipient_keys,
                routing_keys=routing_keys,
                sender_key=sender_verkey,
            )
        ]

    async def _fetch_targets_for_connection_in_progress(
        self, connection: ConnRecord, sender_verkey: str
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from an incomplete `ConnRecord`.

        This covers retrieving targets for connections that are still in the
        process of bootstrapping. This includes connections that are in states
        invitation-received or request-received.

        Args:
            connection: The connection record (with associated `DIDDoc`)
                used to generate the connection target
        Returns:
            A list of `ConnectionTarget` objects
        """
        if (
            connection.invitation_msg_id
            or connection.invitation_key
            or not connection.their_did
        ):  # invitation received or sending request to invitation
            async with self._profile.session() as session:
                invitation = await connection.retrieve_invitation(session)
            targets = await self._fetch_connection_targets_for_invitation(
                connection,
                invitation,
                sender_verkey,
            )
        else:  # sending implicit request
            if connection.their_did:
                # request is implicit; did isn't set if we've received an
                # invitation, only the invitation key
                invitation = None
                did = connection.their_did
                (
                    endpoint,
                    recipient_keys,
                    routing_keys,
                ) = await self.resolve_invitation(did)
            else:
                raise BaseConnectionManagerError(
                    "Connection is in invalid state to fetch targets"
                )
            targets = [
                ConnectionTarget(
                    did=connection.their_did,
                    endpoint=endpoint,
                    label=invitation.label if invitation else None,
                    recipient_keys=recipient_keys,
                    routing_keys=routing_keys,
                    sender_key=sender_verkey,
                )
            ]

        return targets

    async def fetch_connection_targets(
        self, connection: ConnRecord
    ) -> Optional[Sequence[ConnectionTarget]]:
        """Get a list of connection targets from a `ConnRecord`.

        Args:
            connection: The connection record (with associated `DIDDoc`)
                used to generate the connection target
        """

        if not connection.my_did:
            self._logger.debug("No local DID associated with connection")
            return None

        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            my_info = await wallet.get_local_did(connection.my_did)

        if (
            ConnRecord.State.get(connection.state)
            in (ConnRecord.State.INVITATION, ConnRecord.State.REQUEST)
            and ConnRecord.Role.get(connection.their_role) is ConnRecord.Role.RESPONDER
        ):  # invitation received or sending request
            return await self._fetch_targets_for_connection_in_progress(
                connection, my_info.verkey
            )

        if not connection.their_did:
            self._logger.debug("No target DID associated with connection")
            return None

        return await self.resolve_connection_targets(
            connection.their_did, my_info.verkey, connection.their_label
        )

    def diddoc_connection_targets(
        self,
        doc: DIDDoc,
        sender_verkey: str,
        their_label: Optional[str] = None,
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from a DID Document.

        Args:
            doc: The DID Document to create the target from
            sender_verkey: The verkey we are using
            their_label: The connection label they are using
        """
        if not doc:
            raise BaseConnectionManagerError("No DIDDoc provided for connection target")
        if not doc.did:
            raise BaseConnectionManagerError("DIDDoc has no DID")
        if not doc.service:
            raise BaseConnectionManagerError("No services defined by DIDDoc")

        targets = []
        for service in doc.service.values():
            if service.recip_keys:
                targets.append(
                    ConnectionTarget(
                        did=doc.did,
                        endpoint=service.endpoint,
                        label=their_label,
                        recipient_keys=[
                            key.value for key in (service.recip_keys or ())
                        ],
                        routing_keys=[
                            key.value for key in (service.routing_keys or ())
                        ],
                        sender_key=sender_verkey,
                    )
                )
        return targets

    async def fetch_did_document(self, did: str) -> Tuple[DIDDoc, StorageRecord]:
        """Retrieve a DID Document for a given DID.

        Args:
            did: The DID to search for
        """
        async with self._profile.session() as session:
            storage = session.inject(BaseStorage)
            record = await storage.find_record(self.RECORD_TYPE_DID_DOC, {"did": did})
        return DIDDoc.from_json(record.value), record
