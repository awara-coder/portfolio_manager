"""Broker-neutral connector application port."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from typing import Protocol, runtime_checkable

from portfolio_manager.domain import (
    Activity,
    BrokerAccountId,
    BrokerConnectionId,
    Observation,
    TenantId,
    TimeRange,
    as_utc,
)

_KEY = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _require_key(value: str, field_name: str) -> None:
    if _KEY.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a stable lowercase identifier")


class Capability(StrEnum):
    ACCOUNTS = "accounts"
    HOLDINGS = "holdings"
    POSITIONS = "positions"
    BALANCES = "balances"
    ACTIVITIES = "activities"
    INSTRUMENTS = "instruments"
    PRICES = "prices"
    TAX_LOTS = "tax_lots"


@dataclass(frozen=True, slots=True)
class ConnectorDescriptor:
    key: str
    schema_version: str
    capabilities: frozenset[Capability]

    def __post_init__(self) -> None:
        _require_key(self.key, "connector key")
        _require_key(self.schema_version, "connector schema version")
        if not self.capabilities:
            raise ValueError("connector requires at least one capability")


class AuthenticationStatus(StrEnum):
    READY = "ready"
    ACTION_REQUIRED = "action_required"
    EXPIRED = "expired"
    REVOKED = "revoked"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class AuthenticationState:
    status: AuthenticationStatus
    reason_code: str | None = None
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status is AuthenticationStatus.READY:
            if self.reason_code is not None:
                raise ValueError("ready authentication cannot have a failure reason")
        elif self.reason_code is None:
            raise ValueError("non-ready authentication requires a safe reason code")
        if self.reason_code is not None:
            _require_key(self.reason_code, "authentication reason code")
        if self.expires_at is not None:
            object.__setattr__(self, "expires_at", as_utc(self.expires_at, "expires_at"))


@dataclass(frozen=True, slots=True)
class Checkpoint:
    version: str
    value: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _require_key(self.version, "checkpoint version")
        if not self.value:
            raise ValueError("checkpoint value cannot be empty")


@dataclass(frozen=True, slots=True)
class CollectionRequest:
    tenant_id: TenantId
    connection_id: BrokerConnectionId
    capabilities: frozenset[Capability]
    idempotency_key: str
    account_id: BrokerAccountId | None = None
    period: TimeRange | None = None
    checkpoint: Checkpoint | None = None

    def __post_init__(self) -> None:
        if not self.capabilities:
            raise ValueError("collection request requires at least one capability")
        if not self.idempotency_key or self.idempotency_key != self.idempotency_key.strip():
            raise ValueError("idempotency key must be non-empty and trimmed")
        if len(self.idempotency_key) > 200:
            raise ValueError("idempotency key exceeds 200 characters")


@dataclass(frozen=True, slots=True)
class RawArtifact:
    payload: bytes = field(repr=False)
    media_type: str
    retrieved_at: datetime
    connector_key: str
    schema_version: str
    content_digest: str
    source_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.payload:
            raise ValueError("raw artifact payload cannot be empty")
        if not self.media_type or self.media_type != self.media_type.strip():
            raise ValueError("media type must be non-empty and trimmed")
        _require_key(self.connector_key, "connector key")
        _require_key(self.schema_version, "connector schema version")
        if _DIGEST.fullmatch(self.content_digest) is None:
            raise ValueError("content digest must be a lowercase SHA-256 digest")
        if self.content_digest != sha256(self.payload).hexdigest():
            raise ValueError("content digest does not match raw artifact payload")
        object.__setattr__(self, "retrieved_at", as_utc(self.retrieved_at, "retrieved_at"))
        if self.source_at is not None:
            object.__setattr__(self, "source_at", as_utc(self.source_at, "source_at"))

    @classmethod
    def from_payload(
        cls,
        payload: bytes,
        media_type: str,
        retrieved_at: datetime,
        connector_key: str,
        schema_version: str,
        source_at: datetime | None = None,
    ) -> "RawArtifact":
        return cls(
            payload,
            media_type,
            retrieved_at,
            connector_key,
            schema_version,
            sha256(payload).hexdigest(),
            source_at,
        )


class OutcomeStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True, order=True)
class ConnectorIssue:
    code: str

    def __post_init__(self) -> None:
        _require_key(self.code, "connector issue code")


@dataclass(frozen=True, slots=True)
class CapabilityOutcome:
    capability: Capability
    status: OutcomeStatus
    issues: tuple[ConnectorIssue, ...] = ()

    def __post_init__(self) -> None:
        if self.status is OutcomeStatus.SUCCEEDED and self.issues:
            raise ValueError("successful capability outcome cannot have issues")
        if self.status is not OutcomeStatus.SUCCEEDED and not self.issues:
            raise ValueError("non-successful capability outcome requires an issue")
        if len(set(self.issues)) != len(self.issues):
            raise ValueError("capability issues must not be duplicated")


@dataclass(frozen=True, slots=True)
class CollectionResult:
    artifacts: tuple[RawArtifact, ...]
    outcomes: tuple[CapabilityOutcome, ...]
    next_checkpoint: Checkpoint | None = None
    coverage: TimeRange | None = None

    def __post_init__(self) -> None:
        if not self.outcomes:
            raise ValueError("collection result requires at least one capability outcome")
        capabilities = [outcome.capability for outcome in self.outcomes]
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("collection result cannot repeat capability outcomes")


class ConnectorFailureKind(StrEnum):
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    TRANSIENT = "transient"
    VALIDATION = "validation"
    UNSUPPORTED = "unsupported"
    PERMANENT = "permanent"


class ConnectorError(Exception):
    def __init__(
        self,
        kind: ConnectorFailureKind,
        reason_code: str,
        *,
        retry_after: timedelta | None = None,
    ) -> None:
        _require_key(reason_code, "connector error reason code")
        if retry_after is not None and retry_after <= timedelta(0):
            raise ValueError("retry_after must be positive")
        self.kind = kind
        self.reason_code = reason_code
        self.retry_after = retry_after
        super().__init__(f"{kind.value}:{reason_code}")


@runtime_checkable
class Connector(Protocol):
    async def describe(self) -> ConnectorDescriptor: ...

    async def authentication_state(self) -> AuthenticationState: ...

    async def collect(self, request: CollectionRequest) -> CollectionResult: ...


NormalizedRecord = Activity | Observation


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    records: tuple[NormalizedRecord, ...]
    issues: tuple[ConnectorIssue, ...] = ()


@runtime_checkable
class Normalizer(Protocol):
    @property
    def schema_version(self) -> str: ...

    def normalize(self, artifact: RawArtifact) -> NormalizationResult: ...
