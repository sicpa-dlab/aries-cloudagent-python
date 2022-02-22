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
    TransactionManager as endorser ,
    TransactionManagerError,
)
from ...protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
    is_author_role as is_author,
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
        self.method = "sov"

    @property
    def method(self):
        return self._method
    
    @method.setter
    def method(self, value):
        self._method = value
    
    async def _check_ledger(self, ledger, wallet_type):
        if not ledger:
            reason = "No Indy ledger available"
        if not wallet_type:
            reason += ": missing wallet-type?"
        raise NoIndyLedger(reason)
    
    async def _create_did(self,session, method, options ):
        # Create DID
        wallet = session.inject(BaseWallet)
        # TODO Need to plugin-ify the DIDMethod class
        did_method = DIDMethod.from_method(method)
        if not did_method:
            raise RegistrarError("Unknown DID Method")

        return await wallet.create_local_did(
            did_method,
            # TODO keytype needs to be plugin-fifed too
            key_type=KeyType.from_key_type(options["key_type"])
            or did_method.supported_key_types[0],
        )
         
    async def _retreive_endorsor_did(self, profile, connection_id):
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
        return endorser_info["endorser_did"]


    async def _retreive_endorsor_connection_id(self, profile, options):
        endorser_connection_id = options.get("connection_id")
        # author has not provided a endorser connection id
        if endorser_connection_id is None:
            endorser_connection_id = await get_endorser_connection_id(profile)
        # check if we are an author that needs endorseing with no endorsor
        if endorser_connection_id is None:
            raise RegistrarError("No endorser connection found")
        return endorser_connection_id


    async def _endorse_txn(self, profile, endorser_connection_id, txn, meta_data):
        _endorser = endorser(profile)
        try:
            endorsement = await _endorser.create_record(
                messages_attach=txn["signed_txn"],
                connection_id=endorser_connection_id,
                meta_data=meta_data,
            )
        except StorageError as err:
            raise RegistrarError(err.roll_up) from err
        return _endorser, endorsement


    async def _register_nym(self, ledger, did, verkey, alias, role, endorsed, endorser_did):
        txn = None
        async with ledger:
            try:
                (success, txn) = await ledger.register_nym(
                    did,
                    verkey,
                    alias,
                    role,
                    write_ledger= endorsed, # endorsers will write txn and not authors
                    endorser_did=endorser_did,
                )
            except LedgerTransactionError as err:
                raise RegistrarError(err.roll_up) from err
            except LedgerError as err:
                raise RegistrarError(err.roll_up) from err
            except WalletNotFoundError as err:
                raise RegistrarError(err.roll_up) from err
            except WalletError as err:
                raise RegistrarError(
                    (
                        f"Registered NYM for DID {did} on ledger but could not "
                        f"replace metadata in wallet: {err.roll_up}"
                    )
                ) from err
        return (success, txn)


    async def create(
        self,
        profile: Profile,
        method: Optional[str],
        did: Optional[str] = None,
        document: Optional[dict] = None,
        **options: dict,
    ) -> JobRecord:
        """Create a DID from a given method."""
        raise NotImplementedError
        responder = profile.inject(BaseResponder)
        # TODO Add multi-ledger suppport through (pseudo) did indy method support
        async with profile.session() as session:
            ledger = session.inject_or(BaseLedger)
            await self._check_ledger(ledger, session.settings.get_value("wallet.type"))
            # Create DID
            did_info = await self._create_did(session, method, options)

            # TODO how should this interact with optional did param?
            did, verkey = did_info.did, did_info.verkey

            alias = options.get("alias")
            role = options.get("role")
            if role == "reset":  # indy: empty to reset, null for regular user
                role = ""  # visually: confusing - correct 'reset' to empty string here
            author = is_author(profile)
            if author:
                endorser_connection_id = await self._retreive_endorsor_connection_id()
                endorser_did = self._retreive_endorsor_did(profile, endorser_connection_id)

            (success, txn) = self._register_nym(ledger, did, verkey, alias, role, not author, endorser_did)
            
            meta_data = {"verkey": verkey, "alias": alias, "role": role}
            if author:
                _endorser, endorsement = self._endorse_txn(profile, endorser_connection_id, txn, meta_data)
                # if auto-request, send the request to the endorser
                if profile.settings.get_value("endorser.auto_request"):
                    try:
                        (
                            endorsement,
                            transaction_request,
                        ) = await _endorser.create_request(
                            transaction=endorsement,
                            # TODO see if we need to parameterize these params
                            # expires_time=expires_time,
                            # endorser_write_txn=endorser_write_txn,
                        )
                    except (StorageError, TransactionManagerError) as err:
                        raise RegistrarError(err.roll_up) from err

                    await responder.send(transaction_request, connection_id=endorser_connection_id)
            else:
                await profile.notify(
                    DID_CREATION_TOPIC + did,
                    meta_data,
                )
            # TODO: send attrib txn with doc
            # TODO: Determine what the actual state is here
            return JobRecord(state=JobRecord.STATE_REGISTERED)

    async def update(self, did: str, document: dict, **options: dict) -> JobRecord:
        """Update DID."""
        raise NotImplementedError
        # TODO: send attrib txn with doc
        # TODO: should nym role be updated here?
        # TODO: should key rotation be done here?
        return JobRecord()

    async def deactivate(self, did: str, **options: dict) -> JobRecord:
        """Deactivate DID."""
        raise NotImplementedError
        # TODO: send attrib txn with doc
        return JobRecord()
