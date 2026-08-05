"""Exact numeric primitives without calculation or rounding policy."""

from dataclasses import dataclass
from decimal import Decimal


def _require_finite(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")


@dataclass(frozen=True, slots=True, order=True)
class Currency:
    code: str

    def __post_init__(self) -> None:
        if len(self.code) != 3 or not self.code.isascii() or not self.code.isalpha():
            raise ValueError("currency code must contain three ASCII letters")
        if self.code != self.code.upper():
            raise ValueError("currency code must be uppercase")


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        _require_finite(self.amount, "money amount")

    @classmethod
    def from_text(cls, amount: str, currency: Currency) -> "Money":
        return cls(Decimal(amount), currency)


@dataclass(frozen=True, slots=True)
class Quantity:
    value: Decimal

    def __post_init__(self) -> None:
        _require_finite(self.value, "quantity")

    @classmethod
    def from_text(cls, value: str) -> "Quantity":
        return cls(Decimal(value))


@dataclass(frozen=True, slots=True)
class Price:
    value: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        _require_finite(self.value, "price")
        if self.value < 0:
            raise ValueError("price cannot be negative")

    @classmethod
    def from_text(cls, value: str, currency: Currency) -> "Price":
        return cls(Decimal(value), currency)


@dataclass(frozen=True, slots=True)
class FxRate:
    value: Decimal
    base_currency: Currency
    quote_currency: Currency

    def __post_init__(self) -> None:
        _require_finite(self.value, "FX rate")
        if self.value <= 0:
            raise ValueError("FX rate must be positive")

    @classmethod
    def from_text(
        cls,
        value: str,
        base_currency: Currency,
        quote_currency: Currency,
    ) -> "FxRate":
        return cls(Decimal(value), base_currency, quote_currency)
