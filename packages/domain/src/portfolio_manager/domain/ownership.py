"""Tenant ownership, broker accounts, and instrument identity."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from portfolio_manager.domain.identifiers import (
    BrokerAccountId,
    BrokerConnectionId,
    ExternalCashAccountId,
    InstitutionId,
    InstrumentId,
    ListingId,
    TenantId,
    UserId,
)
from portfolio_manager.domain.numeric import Currency, Price, Quantity
from portfolio_manager.domain.temporal import as_utc


def _require_text(value: str, field_name: str, *, maximum: int) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    if len(value) > maximum:
        raise ValueError(f"{field_name} exceeds {maximum} characters")


_KEY = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


def _require_key(value: str, field_name: str) -> None:
    if _KEY.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a stable lowercase identifier")


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    VIEWER = "viewer"


class AssetClass(StrEnum):
    CASH = "cash"
    EQUITY = "equity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    OPTION = "option"
    FUTURE = "future"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    CFD = "cfd"
    WARRANT = "warrant"
    STRUCTURED_PRODUCT = "structured_product"
    OTHER = "other"


class OptionRight(StrEnum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True, slots=True)
class ExternalIdentifier:
    namespace: str
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_key(self.namespace, "external identifier namespace")
        _require_text(self.value, "external identifier value", maximum=512)


@dataclass(frozen=True, slots=True)
class Tenant:
    id: TenantId
    name: str
    created_at: datetime

    def __post_init__(self) -> None:
        _require_text(self.name, "tenant name", maximum=120)
        object.__setattr__(self, "created_at", as_utc(self.created_at, "created_at"))


@dataclass(frozen=True, slots=True)
class User:
    id: UserId
    display_name: str | None = None

    def __post_init__(self) -> None:
        if self.display_name is not None:
            _require_text(self.display_name, "display name", maximum=120)


@dataclass(frozen=True, slots=True)
class TenantMembership:
    tenant_id: TenantId
    user_id: UserId
    role: MembershipRole
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", as_utc(self.created_at, "created_at"))


@dataclass(frozen=True, slots=True)
class Institution:
    id: InstitutionId
    key: str
    name: str

    def __post_init__(self) -> None:
        _require_key(self.key, "institution key")
        _require_text(self.name, "institution name", maximum=120)


@dataclass(frozen=True, slots=True)
class BrokerConnection:
    id: BrokerConnectionId
    tenant_id: TenantId
    institution_id: InstitutionId
    label: str
    created_at: datetime

    def __post_init__(self) -> None:
        _require_text(self.label, "broker connection label", maximum=120)
        object.__setattr__(self, "created_at", as_utc(self.created_at, "created_at"))


@dataclass(frozen=True, slots=True)
class BrokerAccount:
    id: BrokerAccountId
    tenant_id: TenantId
    connection_id: BrokerConnectionId
    external_id: ExternalIdentifier
    label: str
    base_currency: Currency | None = None

    def __post_init__(self) -> None:
        _require_text(self.label, "broker account label", maximum=120)


@dataclass(frozen=True, slots=True)
class ExternalCashAccount:
    id: ExternalCashAccountId
    tenant_id: TenantId
    institution_id: InstitutionId
    label: str
    currency: Currency
    masked_hint: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _require_text(self.label, "cash account label", maximum=120)
        if self.masked_hint is not None:
            _require_text(self.masked_hint, "masked account hint", maximum=32)


@dataclass(frozen=True, slots=True)
class Instrument:
    id: InstrumentId
    name: str
    asset_class: AssetClass
    multiplier: Quantity | None = None
    underlying_id: InstrumentId | None = None
    expiry: date | None = None
    strike: Price | None = None
    option_right: OptionRight | None = None

    def __post_init__(self) -> None:
        _require_text(self.name, "instrument name", maximum=240)
        if self.multiplier is not None and self.multiplier.value <= 0:
            raise ValueError("instrument multiplier must be positive")
        if self.underlying_id == self.id:
            raise ValueError("instrument cannot be its own underlying")
        option_terms = (self.expiry, self.strike, self.option_right)
        if self.asset_class is AssetClass.OPTION:
            if any(term is None for term in option_terms):
                raise ValueError("option requires expiry, strike, and option right")
        elif any(term is not None for term in option_terms):
            raise ValueError("option terms are allowed only for options")


@dataclass(frozen=True, slots=True)
class Listing:
    id: ListingId
    instrument_id: InstrumentId
    symbol: str
    venue: str
    currency: Currency
    valid_from: date | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        _require_text(self.symbol, "listing symbol", maximum=64)
        _require_text(self.venue, "listing venue", maximum=64)
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("listing validity end cannot precede start")


@dataclass(frozen=True, slots=True)
class BrokerInstrumentMapping:
    tenant_id: TenantId
    connection_id: BrokerConnectionId
    listing_id: ListingId
    external_id: ExternalIdentifier
    valid_from: datetime
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        valid_from = as_utc(self.valid_from, "valid_from")
        object.__setattr__(self, "valid_from", valid_from)
        if self.valid_to is not None:
            valid_to = as_utc(self.valid_to, "valid_to")
            if valid_to < valid_from:
                raise ValueError("mapping validity end cannot precede start")
            object.__setattr__(self, "valid_to", valid_to)
