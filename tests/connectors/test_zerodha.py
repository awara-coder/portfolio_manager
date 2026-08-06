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
    def __init__(self, authentication: AuthenticationState) -> None:
        self.authentication = authentication
        self.requests: list[KiteEndpoint] = []

    async def authentication_state(self) -> AuthenticationState:
        return self.authentication

    async def fetch(self, endpoint: KiteEndpoint) -> KitePayload:
        self.requests.append(endpoint)
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
