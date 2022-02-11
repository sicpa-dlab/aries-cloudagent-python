"""Indy DID Registrar.

Resolution is performed using the IndyLedger class.
"""

import json
from typing import Optional

from ...connections.models.conn_record import ConnRecord
from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError, LedgerTransactionError
from ...ledger.util import notify_did_event
from ...messaging.models.base import BaseModelError
from ...messaging.responder import BaseResponder
from ...protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ...protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
    is_author_role,
)
from ...storage.error import StorageError, StorageNotFoundError
from ...wallet.base import BaseWallet
from ...wallet.did_method import DIDMethod
from ...wallet.error import WalletError, WalletNotFoundError
from ...wallet.key_type import KeyType
from ..base import BaseDidRegistrar, RegistrarError, RegistrarType
from ..models.job import JobRecord


DID_CREATION_TOPIC = "indy_register_did"
class NoIndyLedger(RegistrarError):
    """Raised when there is no Indy ledger instance configured."""


class IndyDIDRegistrar(BaseDidRegistrar):
    """Indy DID Registrar."""

    AGENT_SERVICE_TYPE = "did-communication"

    def __init__(self):
        """Initialize Indy Registrar."""
        super().__init__(RegistrarType.INTERNAL)


    async def _check_ledger(self, ledger, wallet_type):
        if not ledger:
            reason = "No Indy ledger available"
        if not wallet_type:
            reason += ": missing wallet-type?"
        raise NoIndyLedger(reason)
    
    
    async def create(
        self,
        profile: Profile,
        method: Optional[str],
        did: Optional[str] = None,
        document: Optional[dict] = None,
        **options: dict,
    ) -> JobRecord:
        """Create a DID from a given method."""
        responder = profile.inject(BaseResponder)
        # TODO Add multi-ledger suppport through (pseudo) did indy method support
        async with profile.session() as session:
            ledger = session.inject_or(BaseLedger)
            await self._check_ledger(ledger, session.settings.get_value("wallet.type"))

            # Create DID
            wallet = session.inject(BaseWallet)
            # TODO Need to plugin-ify the DIDMethod class
            did_method = DIDMethod.from_method(method)
            if not did_method:
                raise RegistrarError("Unknown DID Method")

            did_info = await wallet.create_local_did(
                did_method,
                # TODO keytype needs to be plugin-ified too
                key_type=KeyType.from_key_type(options["key_type"])
                or did_method.supported_key_types[0],
            )

        # TODO how should this interact with optional did param?
        did, verkey = did_info.did, did_info.verkey

        alias = options.get("alias")
        role = options.get("role")
        if role == "reset":  # indy: empty to reset, null for regular user
            role = ""  # visually: confusing - correct 'reset' to empty string here

        create_transaction_for_endorser = json.loads(
            options.get("create_transaction_for_endorser", "false")
        )
        write_ledger = not create_transaction_for_endorser
        endorser_did = None
        connection_id = options.get("conn_id")

        # check if we need to endorse
        if is_author_role(profile):
            # authors cannot write to the ledger
            write_ledger = False
            create_transaction_for_endorser = True
            if not connection_id:
                # author has not provided a connection id, so determine which to use
                connection_id = await get_endorser_connection_id(profile)
            if not connection_id:
                raise RegistrarError("No endorser connection found")

        if not write_ledger and connection_id:
            try:
                async with profile.session() as session:
                    connection_record = await ConnRecord.retrieve_by_id(
                        session, connection_id
                    )
            except StorageNotFoundError as err:
                raise RegistrarError(err.roll_up) from err
            except BaseModelError as err:
                raise RegistrarError(err.roll_up) from err

            async with profile.session() as session:
                endorser_info = await connection_record.metadata_get(
                    session, "endorser_info"
                )
            if not endorser_info:
                raise RegistrarError(
                    "Endorser Info is not set up in "
                    "connection metadata for this connection record"
                )
            if "endorser_did" not in endorser_info.keys():
                raise RegistrarError(
                    '"endorser_did" is not set in "endorser_info"'
                    " in connection metadata for this connection record"
                )
            endorser_did = endorser_info["endorser_did"]

        success = False
        txn = None
        async with ledger:
            try:
                (success, txn) = await ledger.register_nym(
                    did,
                    verkey,
                    alias,
                    role,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                )
            except LedgerTransactionError as err:
                raise RegistrarError(err.roll_up)
            except LedgerError as err:
                raise RegistrarError(err.roll_up)
            except WalletNotFoundError as err:
                raise RegistrarError(err.roll_up)
            except WalletError as err:
                raise RegistrarError(
                    (
                        f"Registered NYM for DID {did} on ledger but could not "
                        f"replace metadata in wallet: {err.roll_up}"
                    )
                )

        meta_data = {"verkey": verkey, "alias": alias, "role": role}
        if not create_transaction_for_endorser:
            # Notify event
            await profile.notify(
                DID_CREATION_TOPIC + did,
                meta_data,
            )
        else:
            transaction_mgr = TransactionManager(profile)
            try:
                transaction = await transaction_mgr.create_record(
                    messages_attach=txn["signed_txn"],
                    connection_id=connection_id,
                    meta_data=meta_data,
                )
            except StorageError as err:
                raise RegistrarError(err.roll_up) from err

            # if auto-request, send the request to the endorser
            if profile.settings.get_value("endorser.auto_request"):
                try:
                    (
                        transaction,
                        transaction_request,
                    ) = await transaction_mgr.create_request(
                        transaction=transaction,
                        # TODO see if we need to parameterize these params
                        # expires_time=expires_time,
                        # endorser_write_txn=endorser_write_txn,
                    )
                except (StorageError, TransactionManagerError) as err:
                    raise RegistrarError(err.roll_up) from err

                await responder.send(transaction_request, connection_id=connection_id)

        # TODO Determine what the actual state is here
        return JobRecord(state=JobRecord.STATE_REGISTERED)

    async def update(self, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        return JobRecord()

    async def deactivate(self, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        return JobRecord()
