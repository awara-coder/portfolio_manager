"""Application ports for short-lived authorization state."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from portfolio_manager.domain import BrokerConnectionId, TenantId, as_utc


@dataclass(frozen=True, slots=True)
class AuthorizationNonce:
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
    async def issue(self, nonce: AuthorizationNonce) -> None: ...

    async def consume(self, digest: str) -> AuthorizationNonce | None: ...
