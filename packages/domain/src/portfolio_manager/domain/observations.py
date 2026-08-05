"""Immutable claims about portfolio state at a point in time."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from portfolio_manager.domain.identifiers import (
    BrokerAccountId,
    ExternalCashAccountId,
    InstrumentId,
    ListingId,
    ObservationId,
    SourceRecordId,
    TenantId,
)
from portfolio_manager.domain.numeric import FxRate, Money, Price, Quantity
from portfolio_manager.domain.quality import DataQuality
from portfolio_manager.domain.temporal import as_utc


class TaxLotAuthority(StrEnum):
    BROKER_REPORTED = "broker_reported"
    DERIVED = "derived"


@dataclass(frozen=True, slots=True)
class PositionValue:
    broker_account_id: BrokerAccountId
    instrument_id: InstrumentId
    quantity: Quantity


@dataclass(frozen=True, slots=True)
class CashBalanceValue:
    account_id: BrokerAccountId | ExternalCashAccountId
    balance: Money


@dataclass(frozen=True, slots=True)
class PriceValue:
    listing_id: ListingId
    price: Price


@dataclass(frozen=True, slots=True)
class FxRateValue:
    rate: FxRate


@dataclass(frozen=True, slots=True)
class TaxLotValue:
    broker_account_id: BrokerAccountId
    instrument_id: InstrumentId
    quantity: Quantity
    total_cost: Money
    acquisition_date: date
    authority: TaxLotAuthority
    policy_version: str | None = None

    def __post_init__(self) -> None:
        if self.authority is TaxLotAuthority.DERIVED:
            if self.policy_version is None:
                raise ValueError("derived tax lot requires a policy version")
        elif self.policy_version is not None:
            raise ValueError("broker-reported tax lot cannot have a policy version")
        if self.policy_version is not None and (
            not self.policy_version or self.policy_version != self.policy_version.strip()
        ):
            raise ValueError("policy version must be non-empty and trimmed")


ObservationValue = PositionValue | CashBalanceValue | PriceValue | FxRateValue | TaxLotValue


@dataclass(frozen=True, slots=True)
class Observation:
    id: ObservationId
    tenant_id: TenantId
    source_record_id: SourceRecordId
    value: ObservationValue
    as_of: datetime
    ingested_at: datetime
    quality: DataQuality
    supersedes_id: ObservationId | None = None

    def __post_init__(self) -> None:
        if self.supersedes_id == self.id:
            raise ValueError("observation cannot supersede itself")
        object.__setattr__(self, "as_of", as_utc(self.as_of, "as_of"))
        object.__setattr__(self, "ingested_at", as_utc(self.ingested_at, "ingested_at"))
        if self.quality.observed_at != self.as_of:
            raise ValueError("quality observed_at must equal observation as_of")
