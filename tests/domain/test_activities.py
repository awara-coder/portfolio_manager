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
    CorporateActionType,
    Currency,
    FeeCategory,
    InstrumentId,
    InstrumentLeg,
    InstrumentLegRole,
    Money,
    Price,
    Quantity,
    SourceRecordId,
    TaxCategory,
    TenantId,
    TransferDirection,
    TransferId,
    TransferMethod,
)

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
INR = Currency("INR")
USD = Currency("USD")


def cash(value: str, currency: Currency, role: CashLegRole) -> CashLeg:
    return CashLeg(Money(Decimal(value), currency), role)


def activity(
    kind: ActivityKind,
    *legs: InstrumentLeg | CashLeg,
    transfer_id: TransferId | None = None,
    transfer_direction: TransferDirection | None = None,
    transfer_method: TransferMethod | None = None,
    corporate_action_type: CorporateActionType | None = None,
) -> Activity:
    return Activity(
        ActivityId.new(),
        TenantId.new(),
        BrokerAccountId.new(),
        SourceRecordId.new(),
        kind,
        legs,
        NOW,
        NOW,
        transfer_id=transfer_id,
        transfer_direction=transfer_direction,
        transfer_method=transfer_method,
        corporate_action_type=corporate_action_type,
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


def test_trade_leg_preserves_source_execution_price() -> None:
    leg = InstrumentLeg(
        InstrumentId.new(),
        Quantity(Decimal("1")),
        execution_price=Price(Decimal("125.50"), USD),
    )

    assert leg.execution_price == Price(Decimal("125.50"), USD)


def test_corporate_action_requires_and_preserves_subtype() -> None:
    item = activity(
        ActivityKind.CORPORATE_ACTION,
        InstrumentLeg(
            InstrumentId.new(),
            Quantity(Decimal("-1")),
            InstrumentLegRole.CORPORATE_ACTION,
        ),
        corporate_action_type=CorporateActionType.EXPIRATION,
    )

    assert item.corporate_action_type is CorporateActionType.EXPIRATION

    with pytest.raises(ValueError, match="requires a subtype"):
        activity(
            ActivityKind.CORPORATE_ACTION,
            InstrumentLeg(
                InstrumentId.new(),
                Quantity(Decimal("1")),
                InstrumentLegRole.CORPORATE_ACTION,
            ),
        )


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


def test_securities_only_acats_transfer_is_supported() -> None:
    transfer = activity(
        ActivityKind.TRANSFER,
        InstrumentLeg(
            InstrumentId.new(),
            Quantity(Decimal("12")),
            InstrumentLegRole.TRANSFER,
        ),
        transfer_id=TransferId.new(),
        transfer_direction=TransferDirection.OUTBOUND,
        transfer_method=TransferMethod.ACATS,
    )

    assert transfer.transfer_method is TransferMethod.ACATS


def test_acats_sides_share_identity_across_broker_accounts() -> None:
    transfer_id = TransferId.new()
    instrument_id = InstrumentId.new()
    source = activity(
        ActivityKind.TRANSFER,
        InstrumentLeg(instrument_id, Quantity(Decimal("-10")), InstrumentLegRole.TRANSFER),
        cash("-25", USD, CashLegRole.TRANSFER),
        transfer_id=transfer_id,
        transfer_direction=TransferDirection.OUTBOUND,
        transfer_method=TransferMethod.ACATS,
    )
    destination = activity(
        ActivityKind.TRANSFER,
        InstrumentLeg(instrument_id, Quantity(Decimal("10")), InstrumentLegRole.TRANSFER),
        cash("25", USD, CashLegRole.TRANSFER),
        transfer_id=transfer_id,
        transfer_direction=TransferDirection.INBOUND,
        transfer_method=TransferMethod.ACATS,
    )

    assert source.transfer_id == destination.transfer_id
    assert source.broker_account_id != destination.broker_account_id


def test_one_sided_acats_transfer_remains_valid_for_later_reconciliation() -> None:
    transfer = activity(
        ActivityKind.TRANSFER,
        cash("100", USD, CashLegRole.TRANSFER),
        transfer_id=TransferId.new(),
        transfer_direction=TransferDirection.INBOUND,
        transfer_method=TransferMethod.ACATS,
    )

    assert transfer.transfer_direction is TransferDirection.INBOUND


def test_transfer_requires_complete_metadata() -> None:
    with pytest.raises(ValueError, match="identity, direction, and method"):
        activity(ActivityKind.TRANSFER, cash("100", USD, CashLegRole.TRANSFER))


def test_transfer_requires_transfer_role() -> None:
    with pytest.raises(ValueError, match="transfer leg"):
        activity(
            ActivityKind.TRANSFER,
            cash("100", USD, CashLegRole.PRINCIPAL),
            transfer_id=TransferId.new(),
            transfer_direction=TransferDirection.INBOUND,
            transfer_method=TransferMethod.ACATS,
        )


def test_non_transfer_rejects_transfer_metadata() -> None:
    with pytest.raises(ValueError, match="only for transfer"):
        activity(
            ActivityKind.DEPOSIT,
            cash("100", USD, CashLegRole.PRINCIPAL),
            transfer_id=TransferId.new(),
            transfer_direction=TransferDirection.INBOUND,
            transfer_method=TransferMethod.ACATS,
        )


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        (ActivityKind.TRADE, "instrument and cash"),
        (ActivityKind.DIVIDEND, "income leg"),
        (ActivityKind.FEE, "fee leg"),
        (ActivityKind.TAX, "tax leg"),
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
