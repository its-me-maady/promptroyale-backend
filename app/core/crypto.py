import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    # Deterministically derive 32-byte urlsafe base64 key from application JWT_SECRET_KEY
    key_bytes = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_key(plain_key: str) -> str:
    """Encrypt an external AI provider API key at rest (SRS FR-7.3)."""
    return _get_fernet().encrypt(plain_key.encode()).decode()


def decrypt_key(cipher_text: str) -> str:
    """Decrypt an encrypted API key in memory only for authorized API calls (SRS FR-7.4)."""
    return _get_fernet().decrypt(cipher_text.encode()).decode()


def mask_key(key: str) -> str:
    """Produce a safe masked preview of an API key without leaking secret tokens."""
    cleaned = key.strip()
    if len(cleaned) <= 8:
        return "••••••••"
    return f"{cleaned[:4]}••••••••{cleaned[-4:]}"
