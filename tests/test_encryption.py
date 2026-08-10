"""Tests for src/crypto/encryption.py — AES-256-GCM round-trip and
tamper detection (GCM's authenticated-encryption guarantee)."""
import os
import pytest
from cryptography.exceptions import InvalidTag

from src.crypto.encryption import encrypt_field, decrypt_field


@pytest.fixture
def aes_key():
    # Fresh random key per test — isolated from the real key in .env.
    return os.urandom(32)


def test_encrypt_decrypt_round_trip(aes_key):
    original = "1234567890"
    ciphertext, nonce = encrypt_field(original, aes_key)

    # Ciphertext should not equal the plaintext — sanity check that
    # encryption actually transformed the data.
    assert ciphertext != original.encode()

    decrypted = decrypt_field(ciphertext, nonce, aes_key)
    assert decrypted == original


def test_tampered_ciphertext_rejected(aes_key):
    """GCM mode provides authenticated encryption — any modification
    to the ciphertext must be detected and rejected, not silently
    decrypted into garbage."""
    ciphertext, nonce = encrypt_field("1234567890", aes_key)

    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF  # flip one byte

    with pytest.raises(InvalidTag):
        decrypt_field(bytes(tampered), nonce, aes_key)
