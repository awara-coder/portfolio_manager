"""Persistence and object-storage adapters."""

from portfolio_manager.persistence.envelope import (
    EncryptedSecret,
    FileKeyEncryptionKeyProvider,
    KeyEncryptionKey,
    KeyEncryptionKeyProvider,
    SecretDecryptionError,
    decrypt_secret,
    encrypt_secret,
)

__all__ = [
    "EncryptedSecret",
    "FileKeyEncryptionKeyProvider",
    "KeyEncryptionKey",
    "KeyEncryptionKeyProvider",
    "SecretDecryptionError",
    "decrypt_secret",
    "encrypt_secret",
]
