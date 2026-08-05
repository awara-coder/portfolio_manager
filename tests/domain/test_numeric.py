from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_manager.domain import Currency, FxRate, Money, Price, Quantity

INR = Currency("INR")
USD = Currency("USD")


@pytest.mark.parametrize("code", ["inr", "US", "USDT", "U1D", "₹₹₹"])
def test_currency_rejects_invalid_codes(code: str) -> None:
    with pytest.raises(ValueError, match="currency code"):
        Currency(code)


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_exact_values_must_be_finite(value: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        Money(value, INR)
    with pytest.raises(ValueError, match="finite"):
        Quantity(value)
    with pytest.raises(ValueError, match="finite"):
        Price(value, INR)
    with pytest.raises(ValueError, match="finite"):
        FxRate(value, USD, INR)


def test_financial_values_reject_float_input() -> None:
    with pytest.raises(TypeError):
        Money(1.1, INR)  # type: ignore[arg-type]


@given(st.decimals(allow_nan=False, allow_infinity=False))
def test_money_preserves_decimal_exactly(value: Decimal) -> None:
    assert Money(value, INR).amount == value


@given(st.decimals(allow_nan=False, allow_infinity=False))
def test_quantity_supports_signed_and_fractional_values(value: Decimal) -> None:
    assert Quantity(value).value == value


@pytest.mark.parametrize("value", [Decimal("-0.01"), Decimal("-1")])
def test_price_cannot_be_negative(value: Decimal) -> None:
    with pytest.raises(ValueError, match="negative"):
        Price(value, USD)


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-0.1")])
def test_fx_rate_must_be_positive(value: Decimal) -> None:
    with pytest.raises(ValueError, match="positive"):
        FxRate(value, USD, INR)


def test_text_constructors_never_convert_through_float() -> None:
    assert Money.from_text("0.1000000000000000001", INR).amount == Decimal("0.1000000000000000001")
    assert Quantity.from_text("0.00000001").value == Decimal("0.00000001")
    assert Price.from_text("12.34", USD).value == Decimal("12.34")
    assert FxRate.from_text("83.125", USD, INR).value == Decimal("83.125")
