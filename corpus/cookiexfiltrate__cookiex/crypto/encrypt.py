# encrypt.py - Fernet encryption/decryption

from cryptography.fernet import Fernet
import base64
import hashlib

def derive_key_from_passphrase(passphrase: str) -> bytes:
    # Derive a Fernet-compatible key from a passphrase
    sha256 = hashlib.sha256(passphrase.encode()).digest()
    return base64.urlsafe_b64encode(sha256)

def encrypt_data(data: bytes, passphrase: str) -> bytes:
    key = derive_key_from_passphrase(passphrase)
    f = Fernet(key)
    return f.encrypt(data)

def decrypt_data(token: bytes, passphrase: str) -> bytes:
    key = derive_key_from_passphrase(passphrase)
    f = Fernet(key)
    return f.decrypt(token)