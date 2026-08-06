import os
from dataclasses import replace
from pathlib import Path

import pytest

from portfolio_manager.persistence import (
    FileKeyEncryptionKeyProvider,
    KeyEncryptionKey,
    SecretDecryptionError,
    decrypt_secret,
    encrypt_secret,
)


class MemoryProvider:
    def __init__(self, version: str = "local-v1") -> None:
        self.key = KeyEncryptionKey(version, b"k" * 32)

    def current(self) -> KeyEncryptionKey:
        return self.key

    def get(self, version: str) -> KeyEncryptionKey:
        if version != self.key.version:
            raise SecretDecryptionError("missing key")
        return self.key


def test_round_trip_and_metadata_are_secret_safe() -> None:
    encrypted = encrypt_secret(
        b"synthetic-api-secret", b"tenant/connection/api-secret/v1", MemoryProvider()
    )

    assert (
        decrypt_secret(encrypted, b"tenant/connection/api-secret/v1", MemoryProvider())
        == b"synthetic-api-secret"
    )
    assert repr(encrypted).find("synthetic-api-secret") == -1
    assert encrypted.algorithm == "AES-256-GCM+AES-KWP"
    assert encrypted.format_version == 1


def test_each_encryption_uses_fresh_dek_and_nonce() -> None:
    provider = MemoryProvider()
    first = encrypt_secret(b"same", b"scope", provider)
    second = encrypt_secret(b"same", b"scope", provider)

    assert first.nonce != second.nonce
    assert first.wrapped_dek != second.wrapped_dek
    assert first.ciphertext != second.ciphertext


@pytest.mark.parametrize("mutator", ["aad", "ciphertext", "wrapped_dek", "nonce"])
def test_tampering_is_rejected(mutator: str) -> None:
    provider = MemoryProvider()
    encrypted = encrypt_secret(b"secret", b"scope", provider)
    if mutator == "aad":
        aad = b"different"
        changed = encrypted
    else:
        aad = b"scope"
        if mutator == "ciphertext":
            changed = replace(encrypted, ciphertext=_flip_last_byte(encrypted.ciphertext))
        elif mutator == "wrapped_dek":
            changed = replace(encrypted, wrapped_dek=_flip_last_byte(encrypted.wrapped_dek))
        else:
            changed = replace(encrypted, nonce=_flip_last_byte(encrypted.nonce))

    with pytest.raises(SecretDecryptionError):
        decrypt_secret(changed, aad, provider)


def _flip_last_byte(value: bytes) -> bytes:
    return value[:-1] + bytes([value[-1] ^ 1])


def test_unknown_key_version_is_rejected() -> None:
    encrypted = encrypt_secret(b"secret", b"scope", MemoryProvider("v1"))

    with pytest.raises(SecretDecryptionError, match="missing key"):
        decrypt_secret(encrypted, b"scope", MemoryProvider("v2"))


@pytest.mark.parametrize("version", ["", " v1", "v 1", "é"])
def test_key_version_is_a_safe_ascii_identifier(version: str) -> None:
    with pytest.raises(ValueError, match="ASCII identifier"):
        KeyEncryptionKey(version, b"k" * 32)


@pytest.mark.parametrize("associated_data", [b"", b"x" * (8 * 1024 + 1)])
def test_associated_data_is_bounded(associated_data: bytes) -> None:
    with pytest.raises(ValueError, match="associated data"):
        encrypt_secret(b"secret", associated_data, MemoryProvider())


def test_file_provider_requires_owner_only_regular_file(tmp_path: Path) -> None:
    key_path = tmp_path / "root.key"
    key_path.write_bytes(b"r" * 32)
    key_path.chmod(0o600)

    provider = FileKeyEncryptionKeyProvider(key_path, "file-v1")
    assert provider.current().material == b"r" * 32

    key_path.chmod(0o640)
    with pytest.raises(ValueError, match="owner-only"):
        provider.current()


def test_file_provider_rejects_symlink_and_wrong_key_size(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_bytes(b"r" * 32)
    target.chmod(0o600)
    link = tmp_path / "root.key"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="regular"):
        FileKeyEncryptionKeyProvider(link, "file-v1").current()

    target.unlink()
    target.write_bytes(b"short")
    target.chmod(0o600)
    with pytest.raises(ValueError, match="256 bits"):
        FileKeyEncryptionKeyProvider(target, "file-v1").current()


def test_file_provider_rejects_unavailable_version(tmp_path: Path) -> None:
    key_path = tmp_path / "root.key"
    key_path.write_bytes(os.urandom(32))
    key_path.chmod(0o600)
    provider = FileKeyEncryptionKeyProvider(key_path, "file-v1")

    with pytest.raises(SecretDecryptionError, match="unavailable"):
        provider.get("file-v2")
