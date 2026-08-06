"""Atomic PostgreSQL-backed authorization nonce storage."""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.application import AuthorizationNonce
from portfolio_manager.domain import BrokerConnectionId, TenantId
from portfolio_manager.persistence.models import AuthorizationNonceRecord


class NonceConflictError(ValueError):
    """Raised when a nonce digest is already present."""


class SqlAlchemyAuthorizationNonceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(self, nonce: AuthorizationNonce) -> None:
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

    async def consume(self, digest: str) -> AuthorizationNonce | None:
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


def _from_row(row: Mapping[Any, Any]) -> AuthorizationNonce:
    return AuthorizationNonce(
        TenantId(row["tenant_id"]),
        BrokerConnectionId(row["connection_id"]),
        row["digest"],
        row["expires_at"],
        row["created_at"],
    )
