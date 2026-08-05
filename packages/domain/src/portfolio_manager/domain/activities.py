"""Immutable economic activities and typed legs."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from portfolio_manager.domain.identifiers import (
    ActivityId,
    BrokerAccountId,
    InstrumentId,
    SourceRecordId,
    TenantId,
)
from portfolio_manager.domain.numeric import Money, Quantity
from portfolio_manager.domain.temporal import as_utc


class ActivityKind(StrEnum):
    TRADE = "trade"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"
    TAX = "tax"
    TRANSFER = "transfer"
    FX_CONVERSION = "fx_conversion"
    CORPORATE_ACTION = "corporate_action"


class InstrumentLegRole(StrEnum):
    POSITION = "position"
    CORPORATE_ACTION = "corporate_action"


class CashLegRole(StrEnum):
    PRINCIPAL = "principal"
    INCOME = "income"
    FEE = "fee"
    TAX = "tax"
    TRANSFER = "transfer"


class FeeCategory(StrEnum):
    BROKERAGE = "brokerage"
    PLATFORM = "platform"
    EXCHANGE = "exchange"
    REGULATORY = "regulatory"
    DEPOSITORY = "depository"
    BANK = "bank"
    FX = "fx"
    ACCOUNT_MAINTENANCE = "account_maintenance"
    INTEREST = "interest"
    OTHER = "other"


class TaxCategory(StrEnum):
    SECURITIES_TRANSACTION = "securities_transaction"
    COMMODITIES_TRANSACTION = "commodities_transaction"
    GST_VAT = "gst_vat"
    STAMP_DUTY = "stamp_duty"
    DOMESTIC_WITHHOLDING = "domestic_withholding"
    FOREIGN_WITHHOLDING = "foreign_withholding"
    TCS = "tcs"
    OTHER_TRANSACTION = "other_transaction"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class InstrumentLeg:
    instrument_id: InstrumentId
    quantity: Quantity
    role: InstrumentLegRole = InstrumentLegRole.POSITION


@dataclass(frozen=True, slots=True)
class CashLeg:
    money: Money
    role: CashLegRole
    fee_category: FeeCategory | None = None
    tax_category: TaxCategory | None = None
    tax_jurisdiction: str | None = None
    source_label: str | None = None

    def __post_init__(self) -> None:
        if (self.role is CashLegRole.FEE) != (self.fee_category is not None):
            raise ValueError("fee category is required only for fee legs")
        if (self.role is CashLegRole.TAX) != (self.tax_category is not None):
            raise ValueError("tax category is required only for tax legs")
        if self.role is not CashLegRole.TAX and self.tax_jurisdiction is not None:
            raise ValueError("tax jurisdiction is allowed only for tax legs")
        if self.tax_jurisdiction is not None and (
            len(self.tax_jurisdiction) != 2
            or not self.tax_jurisdiction.isascii()
            or not self.tax_jurisdiction.isalpha()
            or self.tax_jurisdiction != self.tax_jurisdiction.upper()
        ):
            raise ValueError("tax jurisdiction must be a two-letter uppercase country code")
        if self.source_label is not None and (
            not self.source_label or self.source_label != self.source_label.strip()
        ):
            raise ValueError("source label must be non-empty and trimmed")


ActivityLeg = InstrumentLeg | CashLeg


@dataclass(frozen=True, slots=True)
class Activity:
    id: ActivityId
    tenant_id: TenantId
    broker_account_id: BrokerAccountId
    source_record_id: SourceRecordId
    kind: ActivityKind
    legs: tuple[ActivityLeg, ...]
    effective_at: datetime
    ingested_at: datetime
    trade_date: date | None = None
    settlement_date: date | None = None
    supersedes_id: ActivityId | None = None

    def __post_init__(self) -> None:
        if not self.legs:
            raise ValueError("activity requires at least one leg")
        if self.supersedes_id == self.id:
            raise ValueError("activity cannot supersede itself")
        if (
            self.settlement_date is not None
            and self.trade_date is not None
            and self.settlement_date < self.trade_date
        ):
            raise ValueError("settlement date cannot precede trade date")
        object.__setattr__(self, "effective_at", as_utc(self.effective_at, "effective_at"))
        object.__setattr__(self, "ingested_at", as_utc(self.ingested_at, "ingested_at"))
        self._validate_leg_shape()

    def _validate_leg_shape(self) -> None:
        instrument_legs = [leg for leg in self.legs if isinstance(leg, InstrumentLeg)]
        cash_legs = [leg for leg in self.legs if isinstance(leg, CashLeg)]
        roles = {leg.role for leg in cash_legs}

        if self.kind is ActivityKind.TRADE and (not instrument_legs or not cash_legs):
            raise ValueError("trade requires instrument and cash legs")
        if (
            self.kind in {ActivityKind.DIVIDEND, ActivityKind.INTEREST}
            and CashLegRole.INCOME not in roles
        ):
            raise ValueError("income activity requires an income leg")
        if self.kind is ActivityKind.FEE and CashLegRole.FEE not in roles:
            raise ValueError("fee activity requires a fee leg")
        if self.kind is ActivityKind.TAX and CashLegRole.TAX not in roles:
            raise ValueError("tax activity requires a tax leg")
        if (
            self.kind in {ActivityKind.DEPOSIT, ActivityKind.WITHDRAWAL}
            and CashLegRole.PRINCIPAL not in roles
        ):
            raise ValueError("cash movement requires a principal leg")
        if self.kind is ActivityKind.TRANSFER and CashLegRole.TRANSFER not in roles:
            raise ValueError("transfer requires a transfer leg")
        if self.kind is ActivityKind.CORPORATE_ACTION and not instrument_legs:
            raise ValueError("corporate action requires an instrument leg")
        if self.kind is ActivityKind.FX_CONVERSION:
            currencies = {leg.money.currency for leg in cash_legs}
            if len(cash_legs) < 2 or len(currencies) < 2:
                raise ValueError("FX conversion requires cash legs in at least two currencies")
