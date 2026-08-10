import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

def hash_message(payload_bytes: bytes) -> bytes:
    """SHA-256 hash of the canonical message bytes (integrity check)."""
    return hashlib.sha256(payload_bytes).digest()

def sign_message(payload_bytes: bytes, private_key) -> bytes:
    """
    Sign the message hash with the service's private key.
    NOTE: private_key here is loaded from a local PEM file for Phase 1 only.
    This is explicitly NOT production-safe — Phase 4 replaces this with
    Vault/GSM-backed key retrieval, and Phase 3 replaces the self-signed
    key with a cert issued by my own mini-CA.
    """
    return private_key.sign(
        payload_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
