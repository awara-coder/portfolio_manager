from uuid import UUID

from portfolio_manager.domain import BrokerAccountId, TenantId


def test_identifier_round_trip() -> None:
    identifier = TenantId.new()

    assert TenantId.parse(str(identifier)) == identifier
    assert identifier.value.version == 4


def test_identifier_aliases_hold_uuid_values() -> None:
    tenant_id: TenantId = TenantId(UUID("d6dfabf8-76a8-4b34-9d4a-7c29d6c905d3"))
    account_id: BrokerAccountId = BrokerAccountId(UUID("476b1eca-b685-4935-a945-561846291f91"))

    assert tenant_id.value != account_id.value
