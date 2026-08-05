"""Explicit portfolio scope shared by consolidated and sliced queries."""

from dataclasses import dataclass

from portfolio_manager.domain.identifiers import (
    BrokerAccountId,
    BrokerConnectionId,
    InstitutionId,
    TenantId,
)


@dataclass(frozen=True, slots=True)
class PortfolioScope:
    tenant_id: TenantId
    institution_ids: frozenset[InstitutionId] = frozenset()
    broker_connection_ids: frozenset[BrokerConnectionId] = frozenset()
    broker_account_ids: frozenset[BrokerAccountId] = frozenset()

    @property
    def is_consolidated(self) -> bool:
        return not (self.institution_ids or self.broker_connection_ids or self.broker_account_ids)
