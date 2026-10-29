"""Password hashing (PBKDF2-HMAC-SHA256 with a random per-user salt)."""
import hashlib
import hmac
import secrets
from typing import Optional, Tuple

from .config import PBKDF2_ITERATIONS


def hash_password(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    """Return (hash_hex, salt_hex). A new random salt is created when none is given."""
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Constant-time comparison of a candidate password against the stored hash."""
    candidate, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, hash_hex)
