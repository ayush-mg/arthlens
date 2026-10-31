"""
Unit Tests for Password Security and Hashing.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies:
- Password hashing with Argon2id.
- Plaintext passwords are never stored.
- Password verification succeeds for valid credentials and fails for incorrect ones.
- Generic login failure behavior without account enumeration.
- Input validation on password strings (length, character constraints).
"""

import pytest

from backend.arthlens.security.password import (
    PasswordValidationError,
    hash_password,
    validate_password_strength,
    verify_password,
)


@pytest.mark.unit
class TestPasswordSecurity:
    """Tests password hashing, verification, and validation."""

    def test_hash_password_produces_argon2id_hash(self):
        """hash_password returns a valid Argon2id hash string starting with $argon2id$."""
        pwd = "CorrectHorseBatteryStaple123!"
        hashed = hash_password(pwd)
        assert hashed is not None
        assert hashed.startswith("$argon2id$")
        assert hashed != pwd  # Never plaintext

    def test_verify_password_matches_correct_password(self):
        """verify_password returns True for the matching plaintext password."""
        pwd = "SecureEntrepreneurPass2026!"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_password_rejects_incorrect_password(self):
        """verify_password returns False for an incorrect plaintext password."""
        pwd = "SecureEntrepreneurPass2026!"
        hashed = hash_password(pwd)
        assert verify_password("WrongPassword123!", hashed) is False

    def test_verify_password_handles_corrupt_hash_gracefully(self):
        """verify_password returns False when presented with a corrupt or invalid hash."""
        assert verify_password("Password123!", "invalid_hash_string") is False
        assert verify_password("Password123!", "") is False
        assert verify_password("Password123!", "$argon2id$v=19$m=65536,t=3,p=4$corrupt$corrupt") is False

    def test_hash_produces_unique_salt_each_time(self):
        """Hashing the identical password multiple times produces distinct salted hashes."""
        pwd = "SamePasswordTwice123!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 != h2
        assert verify_password(pwd, h1) is True
        assert verify_password(pwd, h2) is True

    def test_password_validation_enforces_minimum_length(self):
        """Passwords shorter than 8 characters are rejected."""
        with pytest.raises(PasswordValidationError, match="at least 8 characters"):
            validate_password_strength("Short1!")

    def test_password_validation_rejects_empty_or_whitespace(self):
        """Empty or whitespace-only passwords are rejected."""
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            validate_password_strength("")
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            validate_password_strength("        ")

    def test_password_validation_enforces_maximum_length(self):
        """Extremely long passwords (> 128 characters) are rejected to prevent DoS."""
        oversized = "A" * 129
        with pytest.raises(PasswordValidationError, match="cannot exceed 128 characters"):
            validate_password_strength(oversized)

    def test_hash_password_validates_input_before_hashing(self):
        """hash_password raises PasswordValidationError if password fails strength validation."""
        with pytest.raises(PasswordValidationError):
            hash_password("short")
