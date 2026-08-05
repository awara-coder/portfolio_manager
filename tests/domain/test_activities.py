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
        CashLeg(
            Money(Decimal("-1"), INR),
            CashLegRole.TAX,
            tax_category=TaxCategory.SECURITIES_TRANSACTION,
            tax_jurisdiction="IN",
            source_label="STT",
        ),
    )

    assert len(trade.legs) == 4


def test_tcs_is_distinct_from_fee() -> None:
    tax = activity(
        ActivityKind.TAX,
        CashLeg(Money(Decimal("-200"), INR), CashLegRole.TAX, tax_category=TaxCategory.TCS),
    )

    assert isinstance(tax.legs[0], CashLeg)
    assert tax.legs[0].tax_category is TaxCategory.TCS


def test_foreign_dividend_withholding_retains_jurisdiction() -> None:
    withholding = activity(
        ActivityKind.TAX,
        CashLeg(
            Money(Decimal("-25"), USD),
            CashLegRole.TAX,
            tax_category=TaxCategory.FOREIGN_WITHHOLDING,
            tax_jurisdiction="US",
            source_label="US TAX",
        ),
    )

    assert isinstance(withholding.legs[0], CashLeg)
    assert withholding.legs[0].tax_jurisdiction == "US"


@pytest.mark.parametrize(
    "category",
    [
        TaxCategory.SECURITIES_TRANSACTION,
        TaxCategory.COMMODITIES_TRANSACTION,
        TaxCategory.GST_VAT,
        TaxCategory.STAMP_DUTY,
        TaxCategory.DOMESTIC_WITHHOLDING,
        TaxCategory.FOREIGN_WITHHOLDING,
        TaxCategory.TCS,
        TaxCategory.OTHER_TRANSACTION,
        TaxCategory.OTHER,
    ],
)
def test_supported_tax_categories_remain_distinct(category: TaxCategory) -> None:
    leg = CashLeg(
        Money(Decimal("-1"), INR),
        CashLegRole.TAX,
        tax_category=category,
        tax_jurisdiction="IN",
    )

    assert leg.tax_category is category


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

    with pytest.raises(ValueError, match="jurisdiction"):
        CashLeg(
            Money(Decimal("-1"), INR),
            CashLegRole.FEE,
            fee_category=FeeCategory.REGULATORY,
            tax_jurisdiction="IN",
        )


@pytest.mark.parametrize("jurisdiction", ["in", "IND", "I1", ""])
def test_tax_jurisdiction_requires_country_code_shape(jurisdiction: str) -> None:
    with pytest.raises(ValueError, match="two-letter uppercase"):
        CashLeg(
            Money(Decimal("-1"), INR),
            CashLegRole.TAX,
            tax_category=TaxCategory.TCS,
            tax_jurisdiction=jurisdiction,
        )


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
