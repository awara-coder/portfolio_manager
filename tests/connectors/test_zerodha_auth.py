import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from portfolio_manager.application import AuthorizationNonce, ConnectorError, ConnectorFailureKind
from portfolio_manager.connectors import (
    ApplicationKiteNonceStore,
    HttpxKiteTokenExchanger,
    KiteApiCredentials,
    KiteAuthorizationService,
    KiteSession,
    PendingKiteAuthorization,
)
from portfolio_manager.domain import BrokerConnectionId, TenantId

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
NONCE = "safe_state_value_0123456789abcdef"
API_KEY = "synthetic-api-key"
API_SECRET = "synthetic-api-secret"
REQUEST_TOKEN = "synthetic-request-token"
ACCESS_TOKEN = "synthetic-access-token"


class MemoryNonceStore:
    def __init__(self) -> None:
        self.pending: dict[str, PendingKiteAuthorization] = {}

    async def issue(self, authorization: PendingKiteAuthorization) -> None:
        if authorization.nonce_digest in self.pending:
            raise ValueError("duplicate nonce")
        self.pending[authorization.nonce_digest] = authorization

    async def consume(self, nonce_digest: str) -> PendingKiteAuthorization | None:
        return self.pending.pop(nonce_digest, None)


class FakeTokenExchanger:
    def __init__(self) -> None:
        self.calls: list[tuple[KiteApiCredentials, str]] = []

    async def exchange(self, credentials: KiteApiCredentials, request_token: str) -> KiteSession:
        self.calls.append((credentials, request_token))
        return KiteSession(credentials.api_key, ACCESS_TOKEN, NOW + timedelta(hours=12))


def credentials() -> KiteApiCredentials:
    return KiteApiCredentials(API_KEY, API_SECRET)


def fixed_clock() -> datetime:
    return NOW


def fixed_nonce() -> str:
    return NONCE


class ApplicationMemoryNonceStore:
    def __init__(self) -> None:
        self.issued: list[AuthorizationNonce] = []
        self.next_value: AuthorizationNonce | None = None

    async def issue(self, nonce: AuthorizationNonce) -> None:
        self.issued.append(nonce)

    async def consume(self, _digest: str) -> AuthorizationNonce | None:
        return self.next_value


def test_application_nonce_store_adapter_maps_connector_contract() -> None:
    application_store = ApplicationMemoryNonceStore()
    adapter = ApplicationKiteNonceStore(application_store, fixed_clock)
    pending = PendingKiteAuthorization(
        TenantId.new(), BrokerConnectionId.new(), sha256(NONCE.encode()).hexdigest(), NOW
    )

    asyncio.run(adapter.issue(pending))

    assert application_store.issued == [
        AuthorizationNonce(
            pending.tenant_id,
            pending.connection_id,
            pending.nonce_digest,
            pending.expires_at,
            NOW,
        )
    ]
    application_store.next_value = application_store.issued[0]
    assert asyncio.run(adapter.consume(pending.nonce_digest)) == pending
    application_store.next_value = None
    assert asyncio.run(adapter.consume(pending.nonce_digest)) is None


def authorization_service(
    store: MemoryNonceStore,
    exchanger: FakeTokenExchanger,
    *,
    clock: Callable[[], datetime] = fixed_clock,
    nonce_factory: Callable[[], str] = fixed_nonce,
) -> KiteAuthorizationService:
    return KiteAuthorizationService(store, exchanger, clock, nonce_factory)


def test_start_creates_scoped_hashed_nonce_and_official_login_url() -> None:
    store = MemoryNonceStore()
    exchanger = FakeTokenExchanger()
    tenant_id = TenantId.new()
    connection_id = BrokerConnectionId.new()

    start = asyncio.run(
        authorization_service(store, exchanger).start(tenant_id, connection_id, API_KEY)
    )

    query = parse_qs(urlparse(start.login_url).query)
    redirect_params = parse_qs(query["redirect_params"][0])
    digest = sha256(NONCE.encode()).hexdigest()
    assert query["v"] == ["3"]
    assert query["api_key"] == [API_KEY]
    assert redirect_params == {"state": [NONCE]}
    assert store.pending[digest].tenant_id == tenant_id
    assert store.pending[digest].connection_id == connection_id
    assert store.pending[digest].expires_at == NOW + timedelta(minutes=5)
    assert NONCE not in repr(store.pending[digest])
    assert NONCE not in repr(start)


def test_complete_consumes_state_once_and_returns_scoped_session() -> None:
    store = MemoryNonceStore()
    exchanger = FakeTokenExchanger()
    tenant_id = TenantId.new()
    connection_id = BrokerConnectionId.new()
    service = authorization_service(store, exchanger)
    asyncio.run(service.start(tenant_id, connection_id, API_KEY))

    result = asyncio.run(service.complete(NONCE, REQUEST_TOKEN, credentials()))

    assert result.tenant_id == tenant_id
    assert result.connection_id == connection_id
    assert result.session.access_token == ACCESS_TOKEN
    assert exchanger.calls == [(credentials(), REQUEST_TOKEN)]
    assert API_SECRET not in repr(credentials())
    assert ACCESS_TOKEN not in repr(result)

    with pytest.raises(ConnectorError) as replayed:
        asyncio.run(service.complete(NONCE, REQUEST_TOKEN, credentials()))
    assert replayed.value.reason_code == "auth.state_invalid"


def test_expired_state_is_consumed_without_token_exchange() -> None:
    store = MemoryNonceStore()
    exchanger = FakeTokenExchanger()
    service = authorization_service(store, exchanger, clock=lambda: NOW - timedelta(minutes=6))
    asyncio.run(service.start(TenantId.new(), BrokerConnectionId.new(), API_KEY))
    service = authorization_service(store, exchanger, clock=lambda: NOW)

    with pytest.raises(ConnectorError) as raised:
        asyncio.run(service.complete(NONCE, REQUEST_TOKEN, credentials()))

    assert raised.value.reason_code == "auth.state_expired"
    assert exchanger.calls == []
    assert store.pending == {}


@pytest.mark.parametrize("state", ["short", "contains space" + "x" * 24, "é" * 32])
def test_invalid_callback_state_is_rejected_before_store_access(state: str) -> None:
    store = MemoryNonceStore()
    exchanger = FakeTokenExchanger()

    with pytest.raises(ConnectorError) as raised:
        asyncio.run(
            authorization_service(store, exchanger).complete(state, REQUEST_TOKEN, credentials())
        )

    assert raised.value.reason_code == "auth.state_invalid"


def test_invalid_generated_nonce_is_rejected() -> None:
    store = MemoryNonceStore()
    exchanger = FakeTokenExchanger()

    with pytest.raises(ConnectorError) as raised:
        asyncio.run(
            authorization_service(store, exchanger, nonce_factory=lambda: "unsafe").start(
                TenantId.new(), BrokerConnectionId.new(), API_KEY
            )
        )

    assert raised.value.reason_code == "auth.state_invalid"
    assert store.pending == {}


@pytest.mark.parametrize("value", ["", " leading", "line\nbreak", "é", "x" * 513])
def test_credentials_reject_values_unsafe_for_authentication(value: str) -> None:
    with pytest.raises(ValueError, match="API key"):
        KiteApiCredentials(value, API_SECRET)
    with pytest.raises(ValueError, match="API secret"):
        KiteApiCredentials(API_KEY, value)


def test_pending_authorization_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        PendingKiteAuthorization(TenantId.new(), BrokerConnectionId.new(), "not-a-digest", NOW)


def run_exchange(handler: httpx.MockTransport) -> KiteSession:
    async def run() -> KiteSession:
        async with HttpxKiteTokenExchanger(lambda: NOW, http_transport=handler) as exchanger:
            return await exchanger.exchange(credentials(), REQUEST_TOKEN)

    return asyncio.run(run())


def test_token_exchange_uses_official_checksum_without_sending_api_secret() -> None:
    expected_checksum = sha256(f"{API_KEY}{REQUEST_TOKEN}{API_SECRET}".encode()).hexdigest()

    def handler(request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        assert request.method == "POST"
        assert request.url.path == "/session/token"
        assert request.headers["X-Kite-Version"] == "3"
        assert form == {
            "api_key": [API_KEY],
            "request_token": [REQUEST_TOKEN],
            "checksum": [expected_checksum],
        }
        assert API_SECRET.encode() not in request.content
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "api_key": API_KEY,
                    "access_token": ACCESS_TOKEN,
                    "future_field": "ignored",
                },
                "future_envelope_field": True,
            },
        )

    kite_session = run_exchange(httpx.MockTransport(handler))

    assert kite_session.access_token == ACCESS_TOKEN
    assert kite_session.expires_at == datetime(2026, 8, 7, 0, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("status", "kind", "reason"),
    [
        (400, ConnectorFailureKind.AUTHENTICATION, "auth.exchange_rejected"),
        (403, ConnectorFailureKind.AUTHENTICATION, "auth.exchange_rejected"),
        (429, ConnectorFailureKind.RATE_LIMIT, "provider.rate_limit"),
        (500, ConnectorFailureKind.TRANSIENT, "provider.unavailable"),
        (418, ConnectorFailureKind.PERMANENT, "provider.exchange_failed"),
    ],
)
def test_exchange_http_errors_are_typed(
    status: int, kind: ConnectorFailureKind, reason: str
) -> None:
    with pytest.raises(ConnectorError) as raised:
        run_exchange(httpx.MockTransport(lambda _request: httpx.Response(status)))

    assert raised.value.kind is kind
    assert raised.value.reason_code == reason


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b'{"status":"error"}',
        b'{"status":"success","data":{"api_key":1,"access_token":false}}',
    ],
)
def test_invalid_exchange_payload_is_secret_safe(payload: bytes) -> None:
    with pytest.raises(ConnectorError) as raised:
        run_exchange(httpx.MockTransport(lambda _request: httpx.Response(200, content=payload)))

    assert raised.value.reason_code == "provider.invalid_response"
    assert payload.decode(errors="ignore") not in str(raised.value)


def test_exchange_rejects_api_key_mismatch() -> None:
    response = {"status": "success", "data": {"api_key": "other-key", "access_token": ACCESS_TOKEN}}

    with pytest.raises(ConnectorError) as raised:
        run_exchange(httpx.MockTransport(lambda _request: httpx.Response(200, json=response)))

    assert raised.value.reason_code == "provider.api_key_mismatch"


def test_exchange_rejects_unsafe_access_token() -> None:
    response = {"status": "success", "data": {"api_key": API_KEY, "access_token": "bad\ntoken"}}

    with pytest.raises(ConnectorError) as raised:
        run_exchange(httpx.MockTransport(lambda _request: httpx.Response(200, json=response)))

    assert raised.value.reason_code == "provider.invalid_response"


def test_exchange_rejects_oversized_response() -> None:
    with pytest.raises(ConnectorError) as raised:
        run_exchange(
            httpx.MockTransport(
                lambda _request: httpx.Response(200, content=b"x" * (1024 * 1024 + 1))
            )
        )

    assert raised.value.reason_code == "provider.response_too_large"


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (httpx.ReadTimeout("timeout"), "provider.timeout"),
        (httpx.ConnectError("network"), "provider.network_error"),
    ],
)
def test_exchange_network_failures_are_typed(failure: httpx.HTTPError, reason: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        failure.request = request
        raise failure

    with pytest.raises(ConnectorError) as raised:
        run_exchange(httpx.MockTransport(handler))

    assert raised.value.kind is ConnectorFailureKind.TRANSIENT
    assert raised.value.reason_code == reason
