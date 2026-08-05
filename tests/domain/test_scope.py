from portfolio_manager.domain import (
    BrokerAccountId,
    BrokerConnectionId,
    InstitutionId,
    PortfolioScope,
    TenantId,
)


def test_scope_without_filters_is_consolidated() -> None:
    assert PortfolioScope(TenantId.new()).is_consolidated


def test_scope_can_slice_by_multiple_dimensions() -> None:
    scope = PortfolioScope(
        tenant_id=TenantId.new(),
        institution_ids=frozenset({InstitutionId.new()}),
        broker_connection_ids=frozenset({BrokerConnectionId.new()}),
        broker_account_ids=frozenset({BrokerAccountId.new()}),
    )

    assert not scope.is_consolidated
