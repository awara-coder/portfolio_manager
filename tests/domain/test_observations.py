from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from portfolio_manager.domain import (
    Authority,
    BrokerAccountId,
    CashBalanceValue,
    Completeness,
    Currency,
    DataQuality,
    FxRate,
    FxRateValue,
    InstrumentId,
    ListingId,
    Money,
    Observation,
    ObservationId,
    ObservationValue,
    PositionValue,
    Price,
    PriceValue,
    Quantity,
    SourceRecordId,
    TaxLotAuthority,
    TaxLotValue,
    TenantId,
)

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
USD = Currency("USD")
INR = Currency("INR")


def observation(value: ObservationValue, *, quality_time: datetime = NOW) -> Observation:
    return Observation(
        ObservationId.new(),
        TenantId.new(),
        SourceRecordId.new(),
        value,
        NOW,
        NOW,
        DataQuality(Authority.AUTHORITATIVE, Completeness.COMPLETE, quality_time),
    )


@pytest.mark.parametrize(
    "value",
    [
        PositionValue(BrokerAccountId.new(), InstrumentId.new(), Quantity(Decimal("0"))),
        CashBalanceValue(BrokerAccountId.new(), Money(Decimal("0"), USD)),
        PriceValue(ListingId.new(), Price(Decimal("12.34"), USD)),
        FxRateValue(FxRate(Decimal("83.5"), USD, INR)),
    ],
)
def test_observation_supports_broker_neutral_values(value: ObservationValue) -> None:
    assert observation(value).value is value


def test_confirmed_zero_is_an_explicit_observation() -> None:
    value = PositionValue(BrokerAccountId.new(), InstrumentId.new(), Quantity(Decimal("0")))
    item = observation(value)

    assert isinstance(item.value, PositionValue)
    assert item.value.quantity == Quantity(Decimal("0"))


def test_observation_normalizes_times_to_utc() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    as_of = datetime(2026, 8, 5, 17, 30, tzinfo=ist)
    item = Observation(
        ObservationId.new(),
        TenantId.new(),
        SourceRecordId.new(),
        PriceValue(ListingId.new(), Price(Decimal("1"), USD)),
        as_of,
        as_of,
        DataQuality(Authority.AUTHORITATIVE, Completeness.COMPLETE, as_of),
    )

    assert item.as_of == NOW


def test_quality_time_must_describe_same_claim() -> None:
    with pytest.raises(ValueError, match="observed_at"):
        observation(
            CashBalanceValue(BrokerAccountId.new(), Money(Decimal("1"), USD)),
            quality_time=NOW - timedelta(days=1),
        )


def test_observation_cannot_supersede_itself() -> None:
    identifier = ObservationId.new()
    with pytest.raises(ValueError, match="supersede itself"):
        Observation(
            identifier,
            TenantId.new(),
            SourceRecordId.new(),
            CashBalanceValue(BrokerAccountId.new(), Money(Decimal("1"), USD)),
            NOW,
            NOW,
            DataQuality(Authority.AUTHORITATIVE, Completeness.COMPLETE, NOW),
            supersedes_id=identifier,
        )


def test_derived_tax_lot_requires_policy_version() -> None:
    with pytest.raises(ValueError, match="policy version"):
        TaxLotValue(
            BrokerAccountId.new(),
            InstrumentId.new(),
            Quantity(Decimal("1")),
            Money(Decimal("100"), USD),
            date(2025, 1, 1),
            TaxLotAuthority.DERIVED,
        )


def test_broker_tax_lot_cannot_claim_derived_policy() -> None:
    with pytest.raises(ValueError, match="cannot have"):
        TaxLotValue(
            BrokerAccountId.new(),
            InstrumentId.new(),
            Quantity(Decimal("1")),
            Money(Decimal("100"), USD),
            date(2025, 1, 1),
            TaxLotAuthority.BROKER_REPORTED,
            policy_version="fifo-v1",
        )
