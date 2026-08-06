from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.schema import CreateTable

from portfolio_manager.persistence.models import Base


def test_auth_schema_contains_only_tenant_scoped_sensitive_tables() -> None:
    assert set(Base.metadata.tables) == {
        "tenants",
        "institutions",
        "broker_connections",
        "encrypted_secrets",
        "authorization_nonces",
    }
    assert "ciphertext" in Base.metadata.tables["encrypted_secrets"].c
    assert "digest" in Base.metadata.tables["authorization_nonces"].c
    assert Base.metadata.tables["encrypted_secrets"].c.tenant_id.nullable is False
    assert Base.metadata.tables["authorization_nonces"].c.tenant_id.nullable is False


def test_broker_table_compiles_for_postgresql() -> None:
    sql = str(
        CreateTable(Base.metadata.tables["broker_connections"]).compile(
            dialect=PGDialect()  # type: ignore[no-untyped-call]
        )
    )

    assert "tenant_id UUID NOT NULL" in sql
    assert "authentication_expires_at TIMESTAMP WITH TIME ZONE" in sql
    assert "CONSTRAINT uq_broker_connections_tenant_id_id UNIQUE (tenant_id, id)" in sql
