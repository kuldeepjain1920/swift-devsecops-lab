from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_field(plaintext: str, key: bytes) -> tuple[bytes, bytes]:
    """
    Encrypt a single sensitive field (e.g., account_number) using AES-256-GCM.
    GCM mode gives confidentiality AND integrity (authenticated encryption)
    in one step, so a separate MAC isn't needed.
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce, required unique per encryption
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), associated_data=None)
    return ciphertext, nonce

def decrypt_field(ciphertext: bytes, nonce: bytes, key: bytes) -> str:
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    return plaintext.decode()
