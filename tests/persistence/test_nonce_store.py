import asyncio
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.domain import BrokerConnectionId, TenantId
from portfolio_manager.persistence import (
    NonceConflictError,
    SqlAlchemyAuthorizationNonceStore,
    StoredAuthorizationNonce,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
DIGEST = "a" * 64


class FakeResult:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def mappings(self) -> "FakeResult":
        return self

    def one_or_none(self) -> dict[str, Any] | None:
        return self._row


class FakeSession:
    def __init__(
        self, result: FakeResult | None = None, *, flush_error: Exception | None = None
    ) -> None:
        self.added: list[Any] = []
        self.result = result or FakeResult(None)
        self.flush_error = flush_error
        self.executed: list[Any] = []

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        if self.flush_error is not None:
            raise self.flush_error

    async def execute(self, statement: Any) -> FakeResult:
        self.executed.append(statement)
        return self.result


def nonce() -> StoredAuthorizationNonce:
    return StoredAuthorizationNonce(
        TenantId(uuid4()), BrokerConnectionId(uuid4()), DIGEST, NOW, NOW
    )


def test_issue_adds_tenant_bound_nonce() -> None:
    session = FakeSession()
    value = nonce()

    asyncio.run(SqlAlchemyAuthorizationNonceStore(cast(AsyncSession, session)).issue(value))

    assert session.added[0].digest == DIGEST
    assert session.added[0].tenant_id == value.tenant_id.value
    assert session.added[0].connection_id == value.connection_id.value


def test_duplicate_issue_is_translated_without_secret_details() -> None:
    error = IntegrityError("insert", {}, RuntimeError("duplicate"))
    session = FakeSession(flush_error=error)

    with pytest.raises(NonceConflictError, match="already exists") as raised:
        asyncio.run(SqlAlchemyAuthorizationNonceStore(cast(AsyncSession, session)).issue(nonce()))

    assert "duplicate" not in str(raised.value)


def test_consume_deletes_and_returns_the_scoped_nonce() -> None:
    value = nonce()
    session = FakeSession(
        FakeResult(
            {
                "tenant_id": value.tenant_id.value,
                "connection_id": value.connection_id.value,
                "digest": value.digest,
                "expires_at": value.expires_at,
                "created_at": value.created_at,
            }
        )
    )

    consumed = asyncio.run(
        SqlAlchemyAuthorizationNonceStore(cast(AsyncSession, session)).consume(DIGEST)
    )

    assert consumed == value
    assert len(session.executed) == 1
    assert "DELETE FROM authorization_nonces" in str(session.executed[0])


def test_missing_consume_returns_none() -> None:
    assert (
        asyncio.run(
            SqlAlchemyAuthorizationNonceStore(cast(AsyncSession, FakeSession())).consume(DIGEST)
        )
        is None
    )


@pytest.mark.parametrize("digest", ["", "b" * 63, "G" * 64])
def test_nonce_digest_is_lowercase_sha256(digest: str) -> None:
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        StoredAuthorizationNonce(TenantId(uuid4()), BrokerConnectionId(uuid4()), digest, NOW, NOW)
