"""Atomic PostgreSQL-backed authorization nonce storage."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.domain import BrokerConnectionId, TenantId, as_utc
from portfolio_manager.persistence.models import AuthorizationNonceRecord


@dataclass(frozen=True, slots=True)
class StoredAuthorizationNonce:
    tenant_id: TenantId
    connection_id: BrokerConnectionId
    digest: str
    expires_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        if len(self.digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.digest
        ):
            raise ValueError("authorization nonce digest must be lowercase SHA-256")
        object.__setattr__(self, "expires_at", as_utc(self.expires_at, "expires_at"))
        object.__setattr__(self, "created_at", as_utc(self.created_at, "created_at"))


class AuthorizationNonceStore(Protocol):
    async def issue(self, nonce: StoredAuthorizationNonce) -> None: ...

    async def consume(self, digest: str) -> StoredAuthorizationNonce | None: ...


class NonceConflictError(ValueError):
    """Raised when a nonce digest is already present."""


class SqlAlchemyAuthorizationNonceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(self, nonce: StoredAuthorizationNonce) -> None:
        self._session.add(
            AuthorizationNonceRecord(
                digest=nonce.digest,
                tenant_id=nonce.tenant_id.value,
                connection_id=nonce.connection_id.value,
                expires_at=nonce.expires_at,
                created_at=nonce.created_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise NonceConflictError("authorization nonce already exists") from error

    async def consume(self, digest: str) -> StoredAuthorizationNonce | None:
        statement = (
            delete(AuthorizationNonceRecord)
            .where(AuthorizationNonceRecord.digest == digest)
            .returning(
                AuthorizationNonceRecord.tenant_id,
                AuthorizationNonceRecord.connection_id,
                AuthorizationNonceRecord.digest,
                AuthorizationNonceRecord.expires_at,
                AuthorizationNonceRecord.created_at,
            )
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return _from_row(row)


def _from_row(row: Mapping[Any, Any]) -> StoredAuthorizationNonce:
    return StoredAuthorizationNonce(
        TenantId(row["tenant_id"]),
        BrokerConnectionId(row["connection_id"]),
        row["digest"],
        row["expires_at"],
        row["created_at"],
    )
