"""
Unit Tests for JWT Creation, Claims, Validation, and Revocation.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies:
- JWT creation with sub, email, roles, jti, exp, iat claims.
- Valid token decoding and claims extraction.
- Expired token rejection.
- Invalid signature / tampered payload rejection.
- Missing required claims rejection.
- Token revocation integration.
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.arthlens.security.tokens import (
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    create_access_token,
    decode_access_token,
)
from backend.arthlens.security.revocation import InMemoryTokenRevocationStore


@pytest.mark.unit
class TestJWTTokens:
    """Tests JWT creation, decoding, validation, and revocation."""

    def test_create_and_decode_valid_token(self):
        """A freshly minted token decodes correctly with all required claims."""
        user_id = "11111111-1111-1111-1111-111111111111"
        email = "entrepreneur@arthlens.org"
        roles = ["ENTREPRENEUR"]

        token, jti = create_access_token(user_id=user_id, email=email, roles=roles)
        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(jti, str)

        claims = decode_access_token(token)
        assert claims["sub"] == user_id
        assert claims["email"] == email
        assert claims["roles"] == roles
        assert claims["jti"] == jti
        assert "exp" in claims
        assert "iat" in claims

    def test_token_expiration_is_enforced(self):
        """Tokens past their expiration time raise TokenExpiredError."""
        user_id = "22222222-2222-2222-2222-222222222222"
        # Create token that expired 10 seconds ago
        token, _ = create_access_token(
            user_id=user_id,
            email="expired@arthlens.org",
            roles=["STEWARD"],
            expires_delta=timedelta(seconds=-10),
        )

        with pytest.raises(TokenExpiredError, match="Token has expired"):
            decode_access_token(token)

    def test_tampered_token_signature_is_rejected(self):
        """Tampering with token content or signature raises TokenInvalidError."""
        token, _ = create_access_token(
            user_id="33333333-3333-3333-3333-333333333333",
            email="tamper@arthlens.org",
            roles=["ADMIN"],
        )

        # Alter token payload
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}broken.{parts[2]}"

        with pytest.raises(TokenInvalidError):
            decode_access_token(tampered_token)

    def test_token_signed_with_different_secret_is_rejected(self):
        """Token signed with another secret key raises TokenInvalidError."""
        import jwt

        payload = {
            "sub": "44444444-4444-4444-4444-444444444444",
            "email": "rogue@arthlens.org",
            "roles": ["ADMIN"],
            "jti": "rogue-jti",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
        }
        rogue_token = jwt.encode(payload, "completely_different_secret_key_32bytes!!", algorithm="HS256")

        with pytest.raises(TokenInvalidError):
            decode_access_token(rogue_token)

    def test_token_missing_required_claims_is_rejected(self):
        """Tokens missing sub, roles, or jti raise TokenInvalidError."""
        import jwt
        from backend.arthlens.infra.config import get_jwt_secret_key

        secret = get_jwt_secret_key()
        # Missing 'roles' claim
        bad_payload = {
            "sub": "55555555-5555-5555-5555-555555555555",
            "email": "noclaim@arthlens.org",
            "jti": "test-jti",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(bad_payload, secret, algorithm="HS256")
        with pytest.raises(TokenInvalidError, match="missing required claim"):
            decode_access_token(token)

    def test_revoked_token_is_rejected(self):
        """A revoked token jti raises TokenRevokedError when revocation store is provided."""
        revocation_store = InMemoryTokenRevocationStore()
        token, jti = create_access_token(
            user_id="66666666-6666-6666-6666-666666666666",
            email="logout@arthlens.org",
            roles=["ENTREPRENEUR"],
        )

        # Before revocation: succeeds
        claims = decode_access_token(token, revocation_store=revocation_store)
        assert claims["jti"] == jti

        # Revoke the token
        revocation_store.revoke(jti=jti, expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc))

        # After revocation: raises TokenRevokedError
        with pytest.raises(TokenRevokedError, match="Token has been revoked"):
            decode_access_token(token, revocation_store=revocation_store)
