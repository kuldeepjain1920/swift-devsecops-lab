"""Tests for src/crypto/signing.py — the core integrity/non-repudiation
guarantee: a signature must verify against the original payload and
must fail against any tampered payload."""
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
import pytest

from src.crypto.signing import hash_message, sign_message


@pytest.fixture
def keypair():
    # Fresh key pair per test — avoids any shared state between tests
    # and doesn't depend on the real keys/signing_key.pem file on disk.
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def test_hash_message_is_sha256_length():
    digest = hash_message(b"some payload")
    assert len(digest) == 32  # SHA-256 always produces a 32-byte digest


def test_signature_verifies_for_correct_payload(keypair):
    private_key, public_key = keypair
    payload = b"payload-bytes"
    signature = sign_message(payload, private_key)

    # Should not raise — this is the positive case proving sign/verify
    # actually round-trips correctly.
    public_key.verify(
        signature, payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )


def test_signature_detects_tampering(keypair):
    """A tampered payload must fail verification — this is the core
    integrity guarantee the whole signing module exists to provide."""
    private_key, public_key = keypair
    original = b"payload-bytes"
    tampered = b"payload-BYTES"  # one case flip — payload has changed
    signature = sign_message(original, private_key)

    with pytest.raises(InvalidSignature):
        public_key.verify(
            signature, tampered,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
