"""Persistence and object-storage adapters."""

from portfolio_manager.application import AuthorizationNonce, AuthorizationNonceStore
from portfolio_manager.persistence.envelope import (
    EncryptedSecret,
    FileKeyEncryptionKeyProvider,
    KeyEncryptionKey,
    KeyEncryptionKeyProvider,
    SecretDecryptionError,
    decrypt_secret,
    encrypt_secret,
)
from portfolio_manager.persistence.models import (
    AuthorizationNonceRecord,
    Base,
    BrokerConnectionRecord,
    EncryptedSecretRecord,
    InstitutionRecord,
    TenantRecord,
)
from portfolio_manager.persistence.nonce_store import (
    NonceConflictError,
    SqlAlchemyAuthorizationNonceStore,
)

StoredAuthorizationNonce = AuthorizationNonce

__all__ = [
    "AuthorizationNonceRecord",
    "AuthorizationNonceStore",
    "Base",
    "BrokerConnectionRecord",
    "EncryptedSecret",
    "EncryptedSecretRecord",
    "FileKeyEncryptionKeyProvider",
    "InstitutionRecord",
    "KeyEncryptionKey",
    "KeyEncryptionKeyProvider",
    "NonceConflictError",
    "SecretDecryptionError",
    "SqlAlchemyAuthorizationNonceStore",
    "StoredAuthorizationNonce",
    "TenantRecord",
    "decrypt_secret",
    "encrypt_secret",
]
