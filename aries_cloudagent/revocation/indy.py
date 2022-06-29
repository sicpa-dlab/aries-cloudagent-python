"""Indy revocation registry management."""

from typing import Sequence

from ..core.profile import Profile
from ..ledger.base import BaseLedger
from ..ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF,
    GET_REVOC_REG_DEF,
    IndyLedgerRequestsExecutor,
)
from ..multitenant.base import BaseMultitenantManager
from ..storage.base import StorageNotFoundError

from .error import RevocationNotSupportedError, RevocationRegistryBadSizeError
from .models.issuer_rev_reg_record import IssuerRevRegRecord
from .models.revocation_registry import RevocationRegistry


class IndyRevocation:
    """Class for managing Indy credential revocation."""

    REV_REG_CACHE = {}

    def __init__(self, profile: Profile):
        """Initialize the IndyRevocation instance."""
        self._profile = profile

    async def init_issuer_registry(
        self,
        cred_def_id: str,
        max_cred_num: int = None,
        revoc_def_type: str = None,
        tag: str = None,
    ) -> "IssuerRevRegRecord":
        """Create a new revocation registry record for a credential definition."""
        multitenant_mgr = self._profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self._profile)
        else:
            ledger_exec_inst = self._profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                cred_def_id,
                txn_record_type=GET_CRED_DEF,
            )
        )[1]
        async with ledger:
            cred_def = await ledger.get_credential_definition(cred_def_id)
        if not cred_def:
            raise RevocationNotSupportedError("Credential definition not found")
        if not cred_def["value"].get("revocation"):
            raise RevocationNotSupportedError(
                "Credential definition does not support revocation"
            )
        if max_cred_num and not (
            RevocationRegistry.MIN_SIZE <= max_cred_num <= RevocationRegistry.MAX_SIZE
        ):
            raise RevocationRegistryBadSizeError(
                f"Bad revocation registry size: {max_cred_num}"
            )

        record = IssuerRevRegRecord(
            cred_def_id=cred_def_id,
            issuer_did=cred_def_id.split(":")[0],
            max_cred_num=max_cred_num,
            revoc_def_type=revoc_def_type,
            tag=tag,
        )
        async with self._profile.session() as session:
            await record.save(session, reason="Init revocation registry")
        return record

    async def get_active_issuer_rev_reg_record(
        self, cred_def_id: str
    ) -> "IssuerRevRegRecord":
        """Return current active registry for issuing a given credential definition.

        Args:
            cred_def_id: ID of the base credential definition
        """
        async with self._profile.session() as session:
            current = sorted(
                await IssuerRevRegRecord.query_by_cred_def_id(
                    session, cred_def_id, IssuerRevRegRecord.STATE_ACTIVE
                )
            )
        if current:
            return current[0]  # active record is oldest published but not full
        raise StorageNotFoundError(
            f"No active issuer revocation record found for cred def id {cred_def_id}"
        )

    async def get_issuer_rev_reg_record(
        self, revoc_reg_id: str
    ) -> "IssuerRevRegRecord":
        """Return a revocation registry record by identifier.

        Args:
            revoc_reg_id: ID of the revocation registry
        """
        async with self._profile.session() as session:
            return await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
                session, revoc_reg_id
            )

    async def list_issuer_registries(self) -> Sequence["IssuerRevRegRecord"]:
        """List the issuer's current revocation registries."""
        async with self._profile.session() as session:
            return await IssuerRevRegRecord.query(session)

    async def get_issuer_rev_reg_delta(
        self, rev_reg_id: str, fro: int = None, to: int = None
    ) -> dict:
        """
        Check ledger for revocation status for a given revocation registry.

        Args:
            rev_reg_id: ID of the revocation registry

        """
        ledger = await self.get_ledger_for_registry(rev_reg_id)
        async with ledger:
            (rev_reg_delta, _) = await ledger.get_revoc_reg_delta(
                rev_reg_id,
                fro,
                to,
            )

        return rev_reg_delta

    async def get_ledger_registry(self, revoc_reg_id: str) -> "RevocationRegistry":
        """Get a revocation registry from the ledger, fetching as necessary."""
        if revoc_reg_id in IndyRevocation.REV_REG_CACHE:
            return IndyRevocation.REV_REG_CACHE[revoc_reg_id]

        ledger = await self.get_ledger_for_registry(revoc_reg_id)

        async with ledger:
            rev_reg = RevocationRegistry.from_definition(
                await ledger.get_revoc_reg_def(revoc_reg_id), True
            )
            IndyRevocation.REV_REG_CACHE[revoc_reg_id] = rev_reg
            return rev_reg

    async def get_ledger_for_registry(self, revoc_reg_id: str) -> "BaseLedger":
        """Get the ledger for the given registry."""
        multitenant_mgr = self._profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self._profile)
        else:
            ledger_exec_inst = self._profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                revoc_reg_id,
                txn_record_type=GET_REVOC_REG_DEF,
            )
        )[1]
        return ledger
