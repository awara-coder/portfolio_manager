"""Versioned envelope encryption primitives for restricted application data."""

from dataclasses import dataclass, field
from pathlib import Path
from secrets import token_bytes
from stat import S_ISREG
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import aead
from cryptography.hazmat.primitives.keywrap import (
    InvalidUnwrap,
    aes_key_unwrap_with_padding,
    aes_key_wrap_with_padding,
)

_ALGORITHM = "AES-256-GCM+AES-KWP"
_FORMAT_VERSION = 1
_KEY_SIZE = 32
_NONCE_SIZE = 12
_MAX_ASSOCIATED_DATA = 8 * 1024


class SecretDecryptionError(ValueError):
    """Raised when encrypted data cannot be authenticated or decrypted."""


@dataclass(frozen=True, slots=True)
class KeyEncryptionKey:
    version: str
    material: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validate_key_version(self.version)
        if not self.material or len(self.material) != _KEY_SIZE:
            raise ValueError("KEK material must be 256 bits")


class KeyEncryptionKeyProvider(Protocol):
    def current(self) -> KeyEncryptionKey: ...

    def get(self, version: str) -> KeyEncryptionKey: ...


@dataclass(frozen=True, slots=True)
class EncryptedSecret:
    """A serialized-ready encrypted value; plaintext is never retained."""

    key_version: str
    wrapped_dek: bytes = field(repr=False)
    nonce: bytes = field(repr=False)
    ciphertext: bytes = field(repr=False)
    algorithm: str = _ALGORITHM
    format_version: int = _FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.algorithm != _ALGORITHM or self.format_version != _FORMAT_VERSION:
            raise ValueError("unsupported encrypted-secret format")
        _validate_key_version(self.key_version)
        if len(self.nonce) != _NONCE_SIZE:
            raise ValueError("encrypted secret nonce must be 96 bits")
        if not self.wrapped_dek or not self.ciphertext:
            raise ValueError("encrypted secret ciphertext fields cannot be empty")


def encrypt_secret(
    plaintext: bytes,
    associated_data: bytes,
    provider: KeyEncryptionKeyProvider,
) -> EncryptedSecret:
    _validate_inputs(plaintext, associated_data)
    key = provider.current()
    dek = token_bytes(_KEY_SIZE)
    nonce = token_bytes(_NONCE_SIZE)
    aad = _bind_associated_data(associated_data, key.version)
    ciphertext = aead.AESGCM(dek).encrypt(nonce, plaintext, aad)
    wrapped_dek = aes_key_wrap_with_padding(key.material, dek)
    return EncryptedSecret(key.version, wrapped_dek, nonce, ciphertext)


def decrypt_secret(
    encrypted: EncryptedSecret,
    associated_data: bytes,
    provider: KeyEncryptionKeyProvider,
) -> bytes:
    _validate_inputs(b"placeholder", associated_data)
    key = provider.get(encrypted.key_version)
    aad = _bind_associated_data(associated_data, key.version)
    try:
        dek = aes_key_unwrap_with_padding(key.material, encrypted.wrapped_dek)
        return aead.AESGCM(dek).decrypt(encrypted.nonce, encrypted.ciphertext, aad)
    except (InvalidTag, InvalidUnwrap, ValueError) as error:
        raise SecretDecryptionError("encrypted secret authentication failed") from error


@dataclass(frozen=True, slots=True)
class FileKeyEncryptionKeyProvider:
    """Load a local KEK from a regular file readable only by its owner."""

    path: Path
    version: str

    def current(self) -> KeyEncryptionKey:
        return self._load()

    def get(self, version: str) -> KeyEncryptionKey:
        if version != self.version:
            raise SecretDecryptionError("requested KEK version is unavailable")
        return self._load()

    def _load(self) -> KeyEncryptionKey:
        metadata = self.path.lstat()
        if not S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            raise ValueError("KEK file must be a regular owner-only file")
        return KeyEncryptionKey(self.version, self.path.read_bytes())


def _validate_inputs(plaintext: bytes, associated_data: bytes) -> None:
    if not isinstance(plaintext, bytes):
        raise TypeError("secret plaintext must be bytes")
    if not associated_data or len(associated_data) > _MAX_ASSOCIATED_DATA:
        raise ValueError("associated data must be non-empty and at most 8 KiB")


def _validate_key_version(version: str) -> None:
    if (
        not version
        or version != version.strip()
        or len(version) > 64
        or not version.isascii()
        or any(not (character.isalnum() or character in "._-") for character in version)
    ):
        raise ValueError("KEK version must be a short ASCII identifier")


def _bind_associated_data(associated_data: bytes, key_version: str) -> bytes:
    return b"portfolio-manager:v1\x00" + key_version.encode("ascii") + b"\x00" + associated_data
