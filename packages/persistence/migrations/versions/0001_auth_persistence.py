"""Create tenant-scoped broker authentication persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_auth_persistence"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "tenants",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "institutions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
    )
    op.create_table(
        "broker_connections",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("institution_id", uuid, sa.ForeignKey("institutions.id"), nullable=False),
        sa.Column("connector_key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("authentication_status", sa.String(32), nullable=False),
        sa.Column("authentication_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "id", name="uq_broker_connections_tenant_id_id"),
    )
    op.create_table(
        "encrypted_secrets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("tenant_id", uuid, nullable=False),
        sa.Column("connection_id", uuid, nullable=False),
        sa.Column("secret_kind", sa.String(32), nullable=False),
        sa.Column("algorithm", sa.String(64), nullable=False),
        sa.Column("format_version", sa.Integer, nullable=False),
        sa.Column("key_version", sa.String(64), nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary, nullable=False),
        sa.Column("nonce", sa.LargeBinary, nullable=False),
        sa.Column("ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ("tenant_id", "connection_id"),
            ("broker_connections.tenant_id", "broker_connections.id"),
            name="fk_encrypted_secrets_connection",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id", "connection_id", "secret_kind", name="uq_encrypted_secrets_kind"
        ),
    )
    op.create_table(
        "authorization_nonces",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("tenant_id", uuid, nullable=False),
        sa.Column("connection_id", uuid, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ("tenant_id", "connection_id"),
            ("broker_connections.tenant_id", "broker_connections.id"),
            name="fk_authorization_nonces_connection",
            ondelete="CASCADE",
        ),
    )
    for table in ("broker_connections", "encrypted_secrets", "authorization_nonces"):
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY {table}_tenant_isolation ON {table} "
                "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
                "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
            )
        )


def downgrade() -> None:
    for table in ("authorization_nonces", "encrypted_secrets", "broker_connections"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
        op.drop_table(table)
    op.drop_table("institutions")
    op.drop_table("tenants")
