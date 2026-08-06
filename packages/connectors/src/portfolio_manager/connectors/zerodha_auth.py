"""Interactive Kite authorization with single-use callback state."""

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from hashlib import sha256
from hmac import compare_digest
from typing import Literal, Protocol
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from portfolio_manager.application import ConnectorError, ConnectorFailureKind
from portfolio_manager.connectors.zerodha_http import KiteSession
from portfolio_manager.domain import BrokerConnectionId, TenantId, as_utc

_LOGIN_URL = "https://kite.zerodha.com/connect/login"
_API_URL = "https://api.kite.trade"
_KOLKATA = ZoneInfo("Asia/Kolkata")
_NONCE_TTL = timedelta(minutes=5)
_MAX_AUTH_RESPONSE_BYTES = 1024 * 1024
_TIMEOUT = httpx.Timeout(10.0, connect=5.0, pool=5.0)
_LIMITS = httpx.Limits(max_connections=2, max_keepalive_connections=2)


def _validate_credential(value: str, name: str) -> None:
    if (
        not value
        or value != value.strip()
        or len(value) > 512
        or not value.isascii()
        or any(ord(character) < 33 or ord(character) > 126 for character in value)
    ):
        raise ValueError(f"Kite {name} must be a valid non-empty ASCII value")


@dataclass(frozen=True, slots=True)
class KiteApiCredentials:
    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_credential(self.api_key, "API key")
        _validate_credential(self.api_secret, "API secret")


@dataclass(frozen=True, slots=True)
class PendingKiteAuthorization:
    tenant_id: TenantId
    connection_id: BrokerConnectionId
    nonce_digest: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if len(self.nonce_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.nonce_digest
        ):
            raise ValueError("authorization nonce digest must be lowercase SHA-256")
        object.__setattr__(self, "expires_at", as_utc(self.expires_at, "expires_at"))


@dataclass(frozen=True, slots=True)
class KiteAuthorizationStart:
    login_url: str = field(repr=False)
    expires_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "expires_at", as_utc(self.expires_at, "expires_at"))


@dataclass(frozen=True, slots=True)
class KiteAuthorizationResult:
    tenant_id: TenantId
    connection_id: BrokerConnectionId
    session: KiteSession = field(repr=False)


class KiteNonceStore(Protocol):
    """Store hashed state and atomically remove it on consumption."""

    async def issue(self, authorization: PendingKiteAuthorization) -> None: ...

    async def consume(self, nonce_digest: str) -> PendingKiteAuthorization | None: ...


class KiteTokenExchanger(Protocol):
    async def exchange(
        self, credentials: KiteApiCredentials, request_token: str
    ) -> KiteSession: ...


class KiteAuthorizationService:
    def __init__(
        self,
        nonce_store: KiteNonceStore,
        token_exchanger: KiteTokenExchanger,
        clock: Callable[[], datetime],
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._nonce_store = nonce_store
        self._token_exchanger = token_exchanger
        self._clock = clock
        self._nonce_factory = nonce_factory or (lambda: secrets.token_urlsafe(32))

    async def start(
        self,
        tenant_id: TenantId,
        connection_id: BrokerConnectionId,
        api_key: str,
    ) -> KiteAuthorizationStart:
        _validate_credential(api_key, "API key")
        nonce = self._nonce_factory()
        self._validate_nonce(nonce)
        expires_at = self._now() + _NONCE_TTL
        await self._nonce_store.issue(
            PendingKiteAuthorization(
                tenant_id,
                connection_id,
                self._digest(nonce),
                expires_at,
            )
        )
        redirect_params = urlencode({"state": nonce})
        query = urlencode({"v": "3", "api_key": api_key, "redirect_params": redirect_params})
        return KiteAuthorizationStart(f"{_LOGIN_URL}?{query}", expires_at)

    async def complete(
        self,
        state: str,
        request_token: str,
        credentials: KiteApiCredentials,
    ) -> KiteAuthorizationResult:
        self._validate_nonce(state)
        _validate_credential(request_token, "request token")
        authorization = await self._nonce_store.consume(self._digest(state))
        if authorization is None:
            raise ConnectorError(ConnectorFailureKind.VALIDATION, "auth.state_invalid")
        if authorization.expires_at <= self._now():
            raise ConnectorError(ConnectorFailureKind.VALIDATION, "auth.state_expired")
        session = await self._token_exchanger.exchange(credentials, request_token)
        return KiteAuthorizationResult(
            authorization.tenant_id,
            authorization.connection_id,
            session,
        )

    def _now(self) -> datetime:
        return as_utc(self._clock(), "clock value")

    @staticmethod
    def _digest(nonce: str) -> str:
        return sha256(nonce.encode()).hexdigest()

    @staticmethod
    def _validate_nonce(nonce: str) -> None:
        if (
            not 32 <= len(nonce) <= 128
            or not nonce.isascii()
            or any(not (character.isalnum() or character in "-_") for character in nonce)
        ):
            raise ConnectorError(ConnectorFailureKind.VALIDATION, "auth.state_invalid")


class _TokenData(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, hide_input_in_errors=True)

    api_key: str
    access_token: str


class _TokenEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, hide_input_in_errors=True)

    status: Literal["success"]
    data: _TokenData


class HttpxKiteTokenExchanger:
    def __init__(
        self,
        clock: Callable[[], datetime],
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._clock = clock
        self._client = httpx.AsyncClient(
            base_url=_API_URL,
            timeout=_TIMEOUT,
            limits=_LIMITS,
            transport=http_transport,
            trust_env=False,
        )

    async def __aenter__(self) -> "HttpxKiteTokenExchanger":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def exchange(self, credentials: KiteApiCredentials, request_token: str) -> KiteSession:
        _validate_credential(request_token, "request token")
        checksum = sha256(
            f"{credentials.api_key}{request_token}{credentials.api_secret}".encode()
        ).hexdigest()
        try:
            async with self._client.stream(
                "POST",
                "/session/token",
                headers={"X-Kite-Version": "3"},
                data={
                    "api_key": credentials.api_key,
                    "request_token": request_token,
                    "checksum": checksum,
                },
            ) as response:
                self._raise_for_status(response)
                content = await self._read_bounded(response)
        except httpx.TimeoutException as error:
            raise ConnectorError(ConnectorFailureKind.TRANSIENT, "provider.timeout") from error
        except httpx.NetworkError as error:
            raise ConnectorError(
                ConnectorFailureKind.TRANSIENT, "provider.network_error"
            ) from error

        try:
            envelope = _TokenEnvelope.model_validate_json(content)
        except ValidationError as error:
            raise ConnectorError(
                ConnectorFailureKind.VALIDATION, "provider.invalid_response"
            ) from error
        if not compare_digest(envelope.data.api_key, credentials.api_key):
            raise ConnectorError(ConnectorFailureKind.VALIDATION, "provider.api_key_mismatch")
        try:
            return KiteSession(
                credentials.api_key,
                envelope.data.access_token,
                self._session_expiry(self._now()),
            )
        except ValueError as error:
            raise ConnectorError(
                ConnectorFailureKind.VALIDATION, "provider.invalid_response"
            ) from error

    def _now(self) -> datetime:
        return as_utc(self._clock(), "clock value")

    @staticmethod
    def _session_expiry(observed_at: datetime) -> datetime:
        local_date = observed_at.astimezone(_KOLKATA).date() + timedelta(days=1)
        return datetime.combine(local_date, time(6), tzinfo=_KOLKATA).astimezone(UTC)

    @staticmethod
    async def _read_bounded(response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > _MAX_AUTH_RESPONSE_BYTES:
                raise ConnectorError(ConnectorFailureKind.PERMANENT, "provider.response_too_large")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        if status in {400, 403}:
            raise ConnectorError(ConnectorFailureKind.AUTHENTICATION, "auth.exchange_rejected")
        if status == 429:
            raise ConnectorError(ConnectorFailureKind.RATE_LIMIT, "provider.rate_limit")
        if 500 <= status < 600:
            raise ConnectorError(ConnectorFailureKind.TRANSIENT, "provider.unavailable")
        raise ConnectorError(ConnectorFailureKind.PERMANENT, "provider.exchange_failed")
