import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from portfolio_manager.application import (
    AuthenticationStatus,
    ConnectorError,
    ConnectorFailureKind,
)
from portfolio_manager.connectors import (
    HttpxKiteTransport,
    KiteEndpoint,
    KitePayload,
    KiteSession,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
API_KEY = "synthetic-api-key"
ACCESS_TOKEN = "synthetic-access-token"


def session(
    *, access_token: str | None = ACCESS_TOKEN, expires_at: datetime | None = None
) -> KiteSession:
    return KiteSession(API_KEY, access_token, expires_at)


def run_fetch(
    endpoint: KiteEndpoint,
    handler: httpx.MockTransport,
    *,
    kite_session: KiteSession | None = None,
) -> KitePayload:
    async def run() -> KitePayload:
        async with HttpxKiteTransport(
            kite_session or session(), lambda: NOW, http_transport=handler
        ) as transport:
            return await transport.fetch(endpoint)

    return asyncio.run(run())


@pytest.mark.parametrize(
    ("endpoint", "path"),
    [
        (KiteEndpoint.HOLDINGS, "/portfolio/holdings"),
        (KiteEndpoint.POSITIONS, "/portfolio/positions"),
        (KiteEndpoint.FUNDS, "/user/margins"),
        (KiteEndpoint.ORDERS, "/orders"),
        (KiteEndpoint.TRADES, "/trades"),
        (KiteEndpoint.INSTRUMENTS, "/instruments"),
    ],
)
def test_fetch_uses_only_approved_get_routes(endpoint: KiteEndpoint, path: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == "api.kite.trade"
        assert request.url.path == path
        assert request.headers["X-Kite-Version"] == "3"
        assert request.headers["Authorization"] == f"token {API_KEY}:{ACCESS_TOKEN}"
        media_type = "text/csv" if endpoint is KiteEndpoint.INSTRUMENTS else "application/json"
        return httpx.Response(200, content=b"safe-fixture", headers={"content-type": media_type})

    payload = run_fetch(endpoint, httpx.MockTransport(handler))

    assert payload.body == b"safe-fixture"


def test_session_secrets_are_excluded_from_representations() -> None:
    kite_session = session()

    assert API_KEY not in repr(kite_session)
    assert ACCESS_TOKEN not in repr(kite_session)


@pytest.mark.parametrize("unsafe_token", ["line\nbreak", "tab\tvalue", "non-ascii-é"])
def test_session_rejects_unsafe_header_characters(unsafe_token: str) -> None:
    with pytest.raises(ValueError, match="access token"):
        session(access_token=unsafe_token)


def test_missing_and_expired_sessions_do_not_make_requests() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=b"unexpected")

    for kite_session, expected_status, expected_code in (
        (session(access_token=None), AuthenticationStatus.ACTION_REQUIRED, "session.missing"),
        (
            session(expires_at=NOW - timedelta(seconds=1)),
            AuthenticationStatus.EXPIRED,
            "session.expired",
        ),
    ):
        transport = HttpxKiteTransport(
            kite_session, lambda: NOW, http_transport=httpx.MockTransport(handler)
        )
        state = asyncio.run(transport.authentication_state())
        with pytest.raises(ConnectorError) as raised:
            asyncio.run(transport.fetch(KiteEndpoint.HOLDINGS))
        asyncio.run(transport.aclose())

        assert state.status is expected_status
        assert raised.value.reason_code == expected_code

    assert calls == 0


@pytest.mark.parametrize(
    ("status", "kind", "reason"),
    [
        (400, ConnectorFailureKind.VALIDATION, "provider.invalid_request"),
        (403, ConnectorFailureKind.AUTHENTICATION, "session.expired"),
        (404, ConnectorFailureKind.PERMANENT, "provider.endpoint_unavailable"),
        (500, ConnectorFailureKind.TRANSIENT, "provider.unavailable"),
    ],
)
def test_http_failures_are_translated_without_response_content(
    status: int, kind: ConnectorFailureKind, reason: str
) -> None:
    secret_response = "sensitive-account-response"
    mock = httpx.MockTransport(
        lambda _request: httpx.Response(status, content=secret_response.encode())
    )

    with pytest.raises(ConnectorError) as raised:
        run_fetch(KiteEndpoint.HOLDINGS, mock)

    assert raised.value.kind is kind
    assert raised.value.reason_code == reason
    assert secret_response not in str(raised.value)


def test_rate_limit_preserves_safe_retry_delay() -> None:
    mock = httpx.MockTransport(lambda _request: httpx.Response(429, headers={"retry-after": "12"}))

    with pytest.raises(ConnectorError) as raised:
        run_fetch(KiteEndpoint.HOLDINGS, mock)

    assert raised.value.kind is ConnectorFailureKind.RATE_LIMIT
    assert raised.value.retry_after == timedelta(seconds=12)


def test_network_timeout_is_retryable_and_secret_safe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(f"request failed for {request.url}", request=request)

    with pytest.raises(ConnectorError) as raised:
        run_fetch(KiteEndpoint.HOLDINGS, httpx.MockTransport(handler))

    assert raised.value.kind is ConnectorFailureKind.TRANSIENT
    assert raised.value.reason_code == "provider.timeout"
    assert ACCESS_TOKEN not in str(raised.value)


def test_declared_oversized_response_is_rejected_before_reading() -> None:
    mock = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"content-length": str(17 * 1024 * 1024)},
            content=b"small-but-misdeclared",
        )
    )

    with pytest.raises(ConnectorError) as raised:
        run_fetch(KiteEndpoint.HOLDINGS, mock)

    assert raised.value.kind is ConnectorFailureKind.PERMANENT
    assert raised.value.reason_code == "provider.response_too_large"


@pytest.mark.parametrize("retry_after", ["-1", "1.5", "tomorrow", "999999999999999999999"])
def test_untrusted_retry_after_values_are_ignored(retry_after: str) -> None:
    mock = httpx.MockTransport(
        lambda _request: httpx.Response(429, headers={"retry-after": retry_after})
    )

    with pytest.raises(ConnectorError) as raised:
        run_fetch(KiteEndpoint.HOLDINGS, mock)

    assert raised.value.retry_after is None
