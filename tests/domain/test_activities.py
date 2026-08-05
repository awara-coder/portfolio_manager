from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from portfolio_manager.domain import (
    Activity,
    ActivityId,
    ActivityKind,
    BrokerAccountId,
    CashLeg,
    CashLegRole,
    Currency,
    FeeCategory,
    InstrumentId,
    InstrumentLeg,
    Money,
    Quantity,
    SourceRecordId,
    TaxCategory,
    TenantId,
)

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
INR = Currency("INR")
USD = Currency("USD")


def cash(value: str, currency: Currency, role: CashLegRole) -> CashLeg:
    return CashLeg(Money(Decimal(value), currency), role)


def activity(kind: ActivityKind, *legs: InstrumentLeg | CashLeg) -> Activity:
    return Activity(
        ActivityId.new(),
        TenantId.new(),
        BrokerAccountId.new(),
        SourceRecordId.new(),
        kind,
        legs,
        NOW,
        NOW,
    )


def test_trade_supports_security_cash_fee_and_tax_legs() -> None:
    trade = activity(
        ActivityKind.TRADE,
        InstrumentLeg(InstrumentId.new(), Quantity(Decimal("10.5"))),
        cash("-1000", INR, CashLegRole.PRINCIPAL),
        CashLeg(Money(Decimal("-2"), INR), CashLegRole.FEE, FeeCategory.BROKERAGE),
        CashLeg(Money(Decimal("-1"), INR), CashLegRole.TAX, tax_category=TaxCategory.TRANSACTION),
    )

    assert len(trade.legs) == 4


def test_tcs_is_distinct_from_fee() -> None:
    tax = activity(
        ActivityKind.TAX,
        CashLeg(Money(Decimal("-200"), INR), CashLegRole.TAX, tax_category=TaxCategory.TCS),
    )

    assert isinstance(tax.legs[0], CashLeg)
    assert tax.legs[0].tax_category is TaxCategory.TCS


def test_fx_conversion_requires_two_currencies() -> None:
    conversion = activity(
        ActivityKind.FX_CONVERSION,
        cash("-8300", INR, CashLegRole.PRINCIPAL),
        cash("100", USD, CashLegRole.PRINCIPAL),
    )
    assert len(conversion.legs) == 2

    with pytest.raises(ValueError, match="two currencies"):
        activity(
            ActivityKind.FX_CONVERSION,
            cash("-100", INR, CashLegRole.PRINCIPAL),
            cash("99", INR, CashLegRole.PRINCIPAL),
        )


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        (ActivityKind.TRADE, "instrument and cash"),
        (ActivityKind.DIVIDEND, "income leg"),
        (ActivityKind.FEE, "fee leg"),
        (ActivityKind.TAX, "tax leg"),
        (ActivityKind.TRANSFER, "transfer leg"),
        (ActivityKind.CORPORATE_ACTION, "instrument leg"),
    ],
)
def test_activity_kind_rejects_wrong_leg_shape(kind: ActivityKind, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        activity(kind, cash("1", INR, CashLegRole.PRINCIPAL))


def test_fee_and_tax_categories_are_role_specific() -> None:
    with pytest.raises(ValueError, match="fee category"):
        cash("-1", INR, CashLegRole.FEE)
    with pytest.raises(ValueError, match="tax category"):
        CashLeg(Money(Decimal("-1"), INR), CashLegRole.PRINCIPAL, tax_category=TaxCategory.TCS)


def test_activity_cannot_supersede_itself() -> None:
    identifier = ActivityId.new()
    with pytest.raises(ValueError, match="supersede itself"):
        Activity(
            identifier,
            TenantId.new(),
            BrokerAccountId.new(),
            SourceRecordId.new(),
            ActivityKind.DEPOSIT,
            (cash("100", INR, CashLegRole.PRINCIPAL),),
            NOW,
            NOW,
            supersedes_id=identifier,
        )


def test_settlement_cannot_precede_trade_date() -> None:
    with pytest.raises(ValueError, match="settlement date"):
        Activity(
            ActivityId.new(),
            TenantId.new(),
            BrokerAccountId.new(),
            SourceRecordId.new(),
            ActivityKind.TRADE,
            (
                InstrumentLeg(InstrumentId.new(), Quantity(Decimal("1"))),
                cash("-10", INR, CashLegRole.PRINCIPAL),
            ),
            NOW,
            NOW,
            trade_date=date(2026, 8, 5),
            settlement_date=date(2026, 8, 4),
        )
