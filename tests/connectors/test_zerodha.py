import asyncio
from datetime import UTC, datetime

import pytest

from portfolio_manager.application import (
    AuthenticationState,
    AuthenticationStatus,
    Capability,
    CollectionRequest,
    Connector,
    ConnectorError,
    ConnectorFailureKind,
    OutcomeStatus,
)
from portfolio_manager.connectors import KiteEndpoint, KitePayload, ZerodhaConnector
from portfolio_manager.domain import BrokerConnectionId, TenantId

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class FakeKiteTransport:
    def __init__(
        self,
        authentication: AuthenticationState,
        failures: dict[KiteEndpoint, ConnectorError] | None = None,
    ) -> None:
        self.authentication = authentication
        self.failures = failures or {}
        self.requests: list[KiteEndpoint] = []

    async def authentication_state(self) -> AuthenticationState:
        return self.authentication

    async def fetch(self, endpoint: KiteEndpoint) -> KitePayload:
        self.requests.append(endpoint)
        if failure := self.failures.get(endpoint):
            raise failure
        media_type = "text/csv" if endpoint is KiteEndpoint.INSTRUMENTS else "application/json"
        return KitePayload(f'{{"endpoint":"{endpoint.value}"}}'.encode(), media_type)


def request(*capabilities: Capability) -> CollectionRequest:
    return CollectionRequest(
        TenantId.new(),
        BrokerConnectionId.new(),
        frozenset(capabilities),
        "zerodha-daily-2026-08-05",
    )


def test_declares_only_approved_read_capabilities() -> None:
    connector = ZerodhaConnector(
        FakeKiteTransport(AuthenticationState(AuthenticationStatus.READY)), lambda: NOW
    )

    descriptor = asyncio.run(connector.describe())

    assert isinstance(connector, Connector)
    assert descriptor.key == "zerodha.kite"
    assert descriptor.capabilities == frozenset(
        {
            Capability.HOLDINGS,
            Capability.POSITIONS,
            Capability.BALANCES,
            Capability.ACTIVITIES,
            Capability.INSTRUMENTS,
        }
    )


def test_collects_raw_evidence_for_each_requested_endpoint() -> None:
    transport = FakeKiteTransport(AuthenticationState(AuthenticationStatus.READY))
    connector = ZerodhaConnector(transport, lambda: NOW)

    result = asyncio.run(connector.collect(request(Capability.HOLDINGS, Capability.ACTIVITIES)))

    assert transport.requests == [KiteEndpoint.ORDERS, KiteEndpoint.TRADES, KiteEndpoint.HOLDINGS]
    assert [artifact.schema_version for artifact in result.artifacts] == [
        "orders.v1",
        "trades.v1",
        "holdings.v1",
    ]
    assert all(artifact.retrieved_at == NOW for artifact in result.artifacts)
    assert all(outcome.status is OutcomeStatus.SUCCEEDED for outcome in result.outcomes)


def test_reports_unrequested_connector_capability_as_unsupported() -> None:
    connector = ZerodhaConnector(
        FakeKiteTransport(AuthenticationState(AuthenticationStatus.READY)), lambda: NOW
    )

    result = asyncio.run(connector.collect(request(Capability.TAX_LOTS)))

    assert result.artifacts == ()
    assert result.outcomes[0].status is OutcomeStatus.UNSUPPORTED
    assert result.outcomes[0].issues[0].code == "capability.unsupported"


def test_expired_session_is_visible_and_prevents_collection() -> None:
    state = AuthenticationState(AuthenticationStatus.EXPIRED, "session.expired", NOW)
    connector = ZerodhaConnector(FakeKiteTransport(state), lambda: NOW)

    assert asyncio.run(connector.authentication_state()) == state
    with pytest.raises(ConnectorError) as raised:
        asyncio.run(connector.collect(request(Capability.HOLDINGS)))

    assert raised.value.kind is ConnectorFailureKind.AUTHENTICATION
    assert raised.value.reason_code == "session.expired"


def test_payload_rejects_empty_or_ambiguous_content() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        KitePayload(b"", "application/json")
    with pytest.raises(ValueError, match="trimmed"):
        KitePayload(b"{}", " application/json")


def test_failure_in_one_capability_preserves_other_capability_evidence() -> None:
    transport = FakeKiteTransport(
        AuthenticationState(AuthenticationStatus.READY),
        {
            KiteEndpoint.HOLDINGS: ConnectorError(
                ConnectorFailureKind.TRANSIENT, "provider.unavailable"
            )
        },
    )
    connector = ZerodhaConnector(transport, lambda: NOW)

    result = asyncio.run(connector.collect(request(Capability.HOLDINGS, Capability.POSITIONS)))

    assert [artifact.schema_version for artifact in result.artifacts] == ["positions.v1"]
    outcomes = {outcome.capability: outcome for outcome in result.outcomes}
    assert outcomes[Capability.HOLDINGS].status is OutcomeStatus.FAILED
    assert outcomes[Capability.HOLDINGS].issues[0].code == "provider.unavailable"
    assert outcomes[Capability.POSITIONS].status is OutcomeStatus.SUCCEEDED


def test_activity_collection_is_partial_when_one_daily_endpoint_fails() -> None:
    transport = FakeKiteTransport(
        AuthenticationState(AuthenticationStatus.READY),
        {
            KiteEndpoint.ORDERS: ConnectorError(
                ConnectorFailureKind.RATE_LIMIT, "provider.rate_limit"
            )
        },
    )
    connector = ZerodhaConnector(transport, lambda: NOW)

    result = asyncio.run(connector.collect(request(Capability.ACTIVITIES)))

    assert transport.requests == [KiteEndpoint.ORDERS, KiteEndpoint.TRADES]
    assert [artifact.schema_version for artifact in result.artifacts] == ["trades.v1"]
    assert result.outcomes[0].status is OutcomeStatus.PARTIAL
    assert result.outcomes[0].issues[0].code == "provider.rate_limit"


def test_mid_collection_authentication_failure_stops_further_broker_calls() -> None:
    transport = FakeKiteTransport(
        AuthenticationState(AuthenticationStatus.READY),
        {
            KiteEndpoint.ORDERS: ConnectorError(
                ConnectorFailureKind.AUTHENTICATION, "session.revoked"
            )
        },
    )
    connector = ZerodhaConnector(transport, lambda: NOW)

    result = asyncio.run(connector.collect(request(Capability.ACTIVITIES, Capability.HOLDINGS)))

    assert transport.requests == [KiteEndpoint.ORDERS]
    assert result.artifacts == ()
    assert [outcome.status for outcome in result.outcomes] == [
        OutcomeStatus.FAILED,
        OutcomeStatus.FAILED,
    ]
    assert all(outcome.issues[0].code == "session.revoked" for outcome in result.outcomes)


def test_repeated_endpoint_issue_is_reported_once() -> None:
    repeated = ConnectorError(ConnectorFailureKind.TRANSIENT, "provider.unavailable")
    transport = FakeKiteTransport(
        AuthenticationState(AuthenticationStatus.READY),
        {KiteEndpoint.ORDERS: repeated, KiteEndpoint.TRADES: repeated},
    )
    connector = ZerodhaConnector(transport, lambda: NOW)

    result = asyncio.run(connector.collect(request(Capability.ACTIVITIES)))

    assert result.outcomes[0].status is OutcomeStatus.FAILED
    assert result.outcomes[0].issues[0].code == "provider.unavailable"
    assert len(result.outcomes[0].issues) == 1
