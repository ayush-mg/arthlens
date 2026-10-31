"""
Password Hashing and Validation Service using Argon2id.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError


class PasswordValidationError(ValueError):
    """Raised when password input fails length or character criteria."""
    pass


# Configured Argon2id hasher with standard parameters
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def validate_password_strength(password: str) -> None:
    """
    Validate password string length and constraints.
    - Non-empty and not just whitespace.
    - Minimum 8 characters.
    - Maximum 128 characters (prevent DoS).
    """
    if not isinstance(password, str) or not password.strip():
        raise PasswordValidationError("Password cannot be empty or whitespace only.")
    if len(password) < 8:
        raise PasswordValidationError("Password must be at least 8 characters long.")
    if len(password) > 128:
        raise PasswordValidationError("Password cannot exceed 128 characters.")


def hash_password(plaintext: str) -> str:
    """
    Hash a plaintext password using Argon2id with unique per-password salt.
    Enforces strength validation prior to hashing.
    """
    validate_password_strength(plaintext)
    return _hasher.hash(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    """
    Verify plaintext password against an Argon2id hash.
    Returns True if valid, False otherwise (including on malformed hashes).
    """
    if not plaintext or not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, plaintext)
    except (VerifyMismatchError, InvalidHashError, VerificationError, Exception):
        return False


__all__ = [
    "PasswordValidationError",
    "validate_password_strength",
    "hash_password",
    "verify_password",
]
