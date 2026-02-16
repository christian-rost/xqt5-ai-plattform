import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from .config import JWT_SECRET

logger = logging.getLogger(__name__)

# Derive a Fernet key from JWT_SECRET (must be 32 url-safe base64-encoded bytes)
_raw = hashlib.sha256(JWT_SECRET.encode()).digest()
_fernet_key = base64.urlsafe_b64encode(_raw)
_fernet = Fernet(_fernet_key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return the ciphertext as a string."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> Optional[str]:
    """Decrypt a ciphertext string. Returns None on failure."""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception) as e:
        logger.error(f"Decryption failed: {e}")
        return None
