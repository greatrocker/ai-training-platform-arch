from cryptography.fernet import Fernet

from .config import settings

_fernet = Fernet(settings.pipeline_encryption_key.encode())


def encrypt_password(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode())


def decrypt_password(ciphertext: bytes) -> str:
    return _fernet.decrypt(bytes(ciphertext)).decode()
