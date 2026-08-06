"""Read-only Zerodha adapter for the broker-neutral connector port."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from portfolio_manager.application import (
    AuthenticationState,
    AuthenticationStatus,
    Capability,
    CapabilityOutcome,
    CollectionRequest,
    CollectionResult,
    ConnectorDescriptor,
    ConnectorError,
    ConnectorFailureKind,
    ConnectorIssue,
    OutcomeStatus,
    RawArtifact,
)


class KiteEndpoint(StrEnum):
    HOLDINGS = "holdings"
    POSITIONS = "positions"
    FUNDS = "funds"
    ORDERS = "orders"
    TRADES = "trades"
    INSTRUMENTS = "instruments"


@dataclass(frozen=True, slots=True)
class KitePayload:
    body: bytes
    media_type: str
    source_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("Kite payload cannot be empty")
        if not self.media_type or self.media_type != self.media_type.strip():
            raise ValueError("Kite payload media type must be non-empty and trimmed")


class KiteTransport(Protocol):
    async def authentication_state(self) -> AuthenticationState: ...

    async def fetch(self, endpoint: KiteEndpoint) -> KitePayload: ...


_ENDPOINTS: dict[Capability, tuple[KiteEndpoint, ...]] = {
    Capability.HOLDINGS: (KiteEndpoint.HOLDINGS,),
    Capability.POSITIONS: (KiteEndpoint.POSITIONS,),
    Capability.BALANCES: (KiteEndpoint.FUNDS,),
    Capability.ACTIVITIES: (KiteEndpoint.ORDERS, KiteEndpoint.TRADES),
    Capability.INSTRUMENTS: (KiteEndpoint.INSTRUMENTS,),
}


class ZerodhaConnector:
    key = "zerodha.kite"
    schema_version = "v1"

    def __init__(self, transport: KiteTransport, clock: Callable[[], datetime]) -> None:
        self._transport = transport
        self._clock = clock

    async def describe(self) -> ConnectorDescriptor:
        return ConnectorDescriptor(self.key, self.schema_version, frozenset(_ENDPOINTS))

    async def authentication_state(self) -> AuthenticationState:
        return await self._transport.authentication_state()

    async def collect(self, request: CollectionRequest) -> CollectionResult:
        authentication = await self.authentication_state()
        if authentication.status is not AuthenticationStatus.READY:
            raise ConnectorError(
                ConnectorFailureKind.AUTHENTICATION,
                authentication.reason_code or "session.not_ready",
            )

        artifacts: list[RawArtifact] = []
        outcomes: list[CapabilityOutcome] = []
        retrieved_at = self._clock()
        authentication_issue: ConnectorIssue | None = None

        for capability in sorted(request.capabilities, key=lambda item: item.value):
            endpoints = _ENDPOINTS.get(capability)
            if endpoints is None:
                outcomes.append(
                    CapabilityOutcome(
                        capability,
                        OutcomeStatus.UNSUPPORTED,
                        (ConnectorIssue("capability.unsupported"),),
                    )
                )
                continue

            if authentication_issue is not None:
                outcomes.append(
                    CapabilityOutcome(
                        capability,
                        OutcomeStatus.FAILED,
                        (authentication_issue,),
                    )
                )
                continue

            successful_endpoints = 0
            issues: list[ConnectorIssue] = []
            for endpoint in endpoints:
                try:
                    payload = await self._transport.fetch(endpoint)
                    artifacts.append(
                        RawArtifact.from_payload(
                            payload.body,
                            payload.media_type,
                            retrieved_at,
                            self.key,
                            f"{endpoint.value}.v1",
                            payload.source_at,
                        )
                    )
                    successful_endpoints += 1
                except ConnectorError as error:
                    issue = ConnectorIssue(error.reason_code)
                    if issue not in issues:
                        issues.append(issue)
                    if error.kind is ConnectorFailureKind.AUTHENTICATION:
                        authentication_issue = issue
                        break

            if not issues:
                status = OutcomeStatus.SUCCEEDED
            elif successful_endpoints:
                status = OutcomeStatus.PARTIAL
            else:
                status = OutcomeStatus.FAILED
            outcomes.append(CapabilityOutcome(capability, status, tuple(issues)))

        return CollectionResult(tuple(artifacts), tuple(outcomes))
