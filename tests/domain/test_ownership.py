from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from portfolio_manager.domain import (
    AssetClass,
    BrokerAccount,
    BrokerAccountId,
    BrokerConnection,
    BrokerConnectionId,
    BrokerInstrumentMapping,
    Currency,
    ExternalCashAccount,
    ExternalCashAccountId,
    ExternalIdentifier,
    Institution,
    InstitutionId,
    Instrument,
    InstrumentId,
    Listing,
    ListingId,
    MembershipRole,
    OptionRight,
    Price,
    Quantity,
    Tenant,
    TenantId,
    TenantMembership,
    User,
    UserId,
)

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
TENANT_ID = TenantId.new()
USER_ID = UserId.new()
INSTITUTION_ID = InstitutionId.new()
CONNECTION_ID = BrokerConnectionId.new()


def test_tenant_and_membership_normalize_creation_time_to_utc() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    local_time = datetime(2026, 8, 5, 17, 30, tzinfo=ist)

    tenant = Tenant(TENANT_ID, "Personal portfolio", local_time)
    membership = TenantMembership(TENANT_ID, USER_ID, MembershipRole.OWNER, local_time)

    assert tenant.created_at == NOW
    assert membership.created_at == NOW


@pytest.mark.parametrize("name", ["", " leading", "trailing "])
def test_human_labels_must_be_non_empty_and_trimmed(name: str) -> None:
    with pytest.raises(ValueError, match="non-empty and trimmed"):
        Tenant(TENANT_ID, name, NOW)


def test_user_display_name_is_optional() -> None:
    assert User(USER_ID).display_name is None


@pytest.mark.parametrize("key", ["Zerodha", "zerodha account", "1zerodha", ""])
def test_institution_key_must_be_stable(key: str) -> None:
    with pytest.raises(ValueError, match="stable lowercase"):
        Institution(INSTITUTION_ID, key, "Zerodha")


def test_broker_account_retains_tenant_and_connection_ownership() -> None:
    connection = BrokerConnection(
        CONNECTION_ID,
        TENANT_ID,
        INSTITUTION_ID,
        "Primary Zerodha",
        NOW,
    )
    account = BrokerAccount(
        BrokerAccountId.new(),
        TENANT_ID,
        connection.id,
        ExternalIdentifier("zerodha.account", "AB1234"),
        "Trading account",
        Currency("INR"),
    )

    assert account.tenant_id == connection.tenant_id
    assert account.connection_id == connection.id


def test_external_identifier_value_is_excluded_from_repr() -> None:
    external_id = ExternalIdentifier("zerodha.account", "sensitive-account-id")

    assert "sensitive-account-id" not in repr(external_id)
    assert "zerodha.account" in repr(external_id)


def test_cash_account_masks_hint_in_repr() -> None:
    account = ExternalCashAccount(
        ExternalCashAccountId.new(),
        TENANT_ID,
        INSTITUTION_ID,
        "Funding account",
        Currency("INR"),
        "ending 1234",
    )

    assert "ending 1234" not in repr(account)


def test_listing_preserves_instrument_identity_separately_from_symbol() -> None:
    instrument = Instrument(InstrumentId.new(), "Example Industries", AssetClass.EQUITY)
    listing = Listing(
        ListingId.new(),
        instrument.id,
        "EXAMPLE",
        "XNSE",
        Currency("INR"),
    )

    assert listing.instrument_id == instrument.id
    assert listing.symbol == "EXAMPLE"


def test_option_preserves_contract_terms() -> None:
    underlying_id = InstrumentId.new()
    option = Instrument(
        InstrumentId.new(),
        "Example call",
        AssetClass.OPTION,
        multiplier=Quantity(Decimal("100")),
        underlying_id=underlying_id,
        expiry=date(2026, 9, 25),
        strike=Price(Decimal("250"), Currency("USD")),
        option_right=OptionRight.CALL,
    )

    assert option.underlying_id == underlying_id
    assert option.multiplier == Quantity(Decimal("100"))


def test_option_requires_complete_contract_terms() -> None:
    with pytest.raises(ValueError, match="requires expiry"):
        Instrument(InstrumentId.new(), "Incomplete option", AssetClass.OPTION)


def test_non_option_rejects_option_terms() -> None:
    with pytest.raises(ValueError, match="only for options"):
        Instrument(
            InstrumentId.new(),
            "Equity",
            AssetClass.EQUITY,
            option_right=OptionRight.PUT,
        )


def test_instrument_multiplier_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        Instrument(
            InstrumentId.new(),
            "Future",
            AssetClass.FUTURE,
            multiplier=Quantity(Decimal("0")),
        )


def test_listing_rejects_reversed_validity() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        Listing(
            ListingId.new(),
            InstrumentId.new(),
            "EXAMPLE",
            "XNSE",
            Currency("INR"),
            valid_from=date(2026, 8, 5),
            valid_to=date(2026, 8, 4),
        )


def test_broker_mapping_normalizes_time_and_rejects_reversed_validity() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        BrokerInstrumentMapping(
            TENANT_ID,
            CONNECTION_ID,
            ListingId.new(),
            ExternalIdentifier("zerodha.instrument", "12345"),
            valid_from=NOW,
            valid_to=NOW - timedelta(seconds=1),
        )
