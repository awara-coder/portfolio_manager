"""SQLAlchemy persistence models for tenant-scoped broker authentication."""

from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid

_UUID: Final = Uuid(as_uuid=True)


class Base(DeclarativeBase):
    pass


class TenantRecord(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InstitutionRecord(Base):
    __tablename__ = "institutions"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class BrokerConnectionRecord(Base):
    __tablename__ = "broker_connections"
    __table_args__ = (
        ForeignKeyConstraint(("tenant_id",), ("tenants.id",), ondelete="CASCADE"),
        UniqueConstraint("tenant_id", "id", name="uq_broker_connections_tenant_id_id"),
    )

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    institution_id: Mapped[UUID] = mapped_column(
        _UUID, ForeignKey("institutions.id"), nullable=False, index=True
    )
    connector_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    authentication_status: Mapped[str] = mapped_column(String(32), nullable=False)
    authentication_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EncryptedSecretRecord(Base):
    __tablename__ = "encrypted_secrets"
    __table_args__ = (
        ForeignKeyConstraint(
            ("tenant_id", "connection_id"),
            ("broker_connections.tenant_id", "broker_connections.id"),
            name="fk_encrypted_secrets_connection",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id", "connection_id", "secret_kind", name="uq_encrypted_secrets_kind"
        ),
    )

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    connection_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    secret_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    format_version: Mapped[int] = mapped_column(Integer, nullable=False)
    key_version: Mapped[str] = mapped_column(String(64), nullable=False)
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthorizationNonceRecord(Base):
    __tablename__ = "authorization_nonces"
    __table_args__ = (
        ForeignKeyConstraint(
            ("tenant_id", "connection_id"),
            ("broker_connections.tenant_id", "broker_connections.id"),
            name="fk_authorization_nonces_connection",
            ondelete="CASCADE",
        ),
    )

    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    connection_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
