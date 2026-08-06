"""Allowlisted asynchronous HTTP transport for Kite Connect v3."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx

from portfolio_manager.application import (
    AuthenticationState,
    AuthenticationStatus,
    ConnectorError,
    ConnectorFailureKind,
)
from portfolio_manager.connectors.zerodha import KiteEndpoint, KitePayload
from portfolio_manager.domain import as_utc

_ROOT_URL = "https://api.kite.trade"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0, pool=5.0)
_LIMITS = httpx.Limits(max_connections=5, max_keepalive_connections=5)
_DEFAULT_MAX_BYTES = 16 * 1024 * 1024
_INSTRUMENTS_MAX_BYTES = 64 * 1024 * 1024

_PATHS = {
    KiteEndpoint.HOLDINGS: "/portfolio/holdings",
    KiteEndpoint.POSITIONS: "/portfolio/positions",
    KiteEndpoint.FUNDS: "/user/margins",
    KiteEndpoint.ORDERS: "/orders",
    KiteEndpoint.TRADES: "/trades",
    KiteEndpoint.INSTRUMENTS: "/instruments",
}


@dataclass(frozen=True, slots=True)
class KiteSession:
    api_key: str = field(repr=False)
    access_token: str | None = field(default=None, repr=False)
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        self._validate_secret(self.api_key, "API key")
        if self.access_token is not None:
            self._validate_secret(self.access_token, "access token")
        if self.expires_at is not None:
            object.__setattr__(self, "expires_at", as_utc(self.expires_at, "expires_at"))

    @staticmethod
    def _validate_secret(value: str, field_name: str) -> None:
        if (
            not value
            or value != value.strip()
            or not value.isascii()
            or any(ord(character) < 33 or ord(character) > 126 for character in value)
        ):
            raise ValueError(f"Kite {field_name} must be a valid non-empty ASCII header value")


class HttpxKiteTransport:
    def __init__(
        self,
        session: KiteSession,
        clock: Callable[[], datetime],
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._session = session
        self._clock = clock
        self._client = httpx.AsyncClient(
            base_url=_ROOT_URL,
            timeout=_TIMEOUT,
            limits=_LIMITS,
            transport=http_transport,
            trust_env=False,
        )

    async def __aenter__(self) -> "HttpxKiteTransport":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def authentication_state(self) -> AuthenticationState:
        if self._session.access_token is None:
            return AuthenticationState(AuthenticationStatus.ACTION_REQUIRED, "session.missing")
        if self._session.expires_at is not None and self._session.expires_at <= self._now():
            return AuthenticationState(
                AuthenticationStatus.EXPIRED,
                "session.expired",
                self._session.expires_at,
            )
        return AuthenticationState(AuthenticationStatus.READY, expires_at=self._session.expires_at)

    async def fetch(self, endpoint: KiteEndpoint) -> KitePayload:
        authentication = await self.authentication_state()
        if authentication.status is not AuthenticationStatus.READY:
            raise ConnectorError(
                ConnectorFailureKind.AUTHENTICATION,
                authentication.reason_code or "session.not_ready",
            )

        try:
            async with self._client.stream(
                "GET",
                _PATHS[endpoint],
                headers=self._headers(),
            ) as response:
                self._raise_for_status(response)
                body = await self._read_bounded(response, self._max_bytes(endpoint))
                media_type = response.headers.get("content-type", "application/octet-stream")
        except httpx.TimeoutException as error:
            raise ConnectorError(ConnectorFailureKind.TRANSIENT, "provider.timeout") from error
        except httpx.NetworkError as error:
            raise ConnectorError(
                ConnectorFailureKind.TRANSIENT, "provider.network_error"
            ) from error

        if not body:
            raise ConnectorError(ConnectorFailureKind.VALIDATION, "provider.empty_response")
        return KitePayload(body, media_type)

    def _headers(self) -> dict[str, str]:
        access_token = self._session.access_token
        if access_token is None:
            raise ConnectorError(ConnectorFailureKind.AUTHENTICATION, "session.missing")
        return {
            "Authorization": f"token {self._session.api_key}:{access_token}",
            "X-Kite-Version": "3",
            "Accept": "application/json, text/csv",
        }

    def _now(self) -> datetime:
        return as_utc(self._clock(), "clock value")

    @staticmethod
    def _max_bytes(endpoint: KiteEndpoint) -> int:
        if endpoint is KiteEndpoint.INSTRUMENTS:
            return _INSTRUMENTS_MAX_BYTES
        return _DEFAULT_MAX_BYTES

    @staticmethod
    async def _read_bounded(response: httpx.Response, limit: int) -> bytes:
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError as error:
                raise ConnectorError(
                    ConnectorFailureKind.VALIDATION, "provider.invalid_content_length"
                ) from error
            if declared_length < 0 or declared_length > limit:
                raise ConnectorError(ConnectorFailureKind.PERMANENT, "provider.response_too_large")

        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > limit:
                raise ConnectorError(ConnectorFailureKind.PERMANENT, "provider.response_too_large")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        if status in {401, 403}:
            raise ConnectorError(ConnectorFailureKind.AUTHENTICATION, "session.expired")
        if status == 429:
            raise ConnectorError(
                ConnectorFailureKind.RATE_LIMIT,
                "provider.rate_limit",
                retry_after=HttpxKiteTransport._retry_after(response),
            )
        if status == 400:
            raise ConnectorError(ConnectorFailureKind.VALIDATION, "provider.invalid_request")
        if status in {404, 405, 410}:
            raise ConnectorError(ConnectorFailureKind.PERMANENT, "provider.endpoint_unavailable")
        if 500 <= status < 600:
            raise ConnectorError(ConnectorFailureKind.TRANSIENT, "provider.unavailable")
        raise ConnectorError(ConnectorFailureKind.PERMISSION, "provider.request_denied")

    @staticmethod
    def _retry_after(response: httpx.Response) -> timedelta | None:
        value = response.headers.get("retry-after")
        if value is None or not value.isascii() or not value.isdecimal():
            return None
        seconds = int(value)
        if seconds <= 0 or seconds > 86_400:
            return None
        return timedelta(seconds=seconds)
