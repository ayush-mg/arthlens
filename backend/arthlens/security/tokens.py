"""
JSON Web Token (JWT) Generation, Validation, and Claim Verification.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError

from backend.arthlens.infra.config import (
    get_access_token_expire_minutes,
    get_jwt_algorithm,
    get_jwt_secret_key,
)
from backend.arthlens.security.revocation import TokenRevocationStore, get_token_revocation_store


class TokenError(Exception):
    """Base exception for authentication token errors."""
    pass


class TokenExpiredError(TokenError):
    """Raised when an authentication token has expired."""
    pass


class TokenInvalidError(TokenError):
    """Raised when token signature, claims, or structure is invalid."""
    pass


class TokenRevokedError(TokenError):
    """Raised when a token has been explicitly revoked upon logout."""
    pass


REQUIRED_CLAIMS = ("sub", "email", "roles", "jti", "exp", "iat")


def create_access_token(
    user_id: str,
    email: str,
    roles: List[str],
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str]:
    """
    Create a signed JWT access token containing standard authentication claims.

    Claims:
    - sub: Authenticated User ID (UUID string)
    - email: User's primary email address
    - roles: List of authorized MVP roles (ENTREPRENEUR, STEWARD, ADMIN)
    - jti: Unique JWT ID for revocation tracking
    - exp: Expiration timestamp in UTC
    - iat: Issued-at timestamp in UTC

    Returns:
        Tuple of (encoded_token_string, jti)
    """
    secret = get_jwt_secret_key()
    algorithm = get_jwt_algorithm()
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=get_access_token_expire_minutes())

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": str(email),
        "roles": list(roles),
        "jti": jti,
        "exp": expire,
        "iat": now,
    }

    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token, jti


def decode_access_token(
    token: str,
    revocation_store: Optional[TokenRevocationStore] = None,
) -> Dict[str, Any]:
    """
    Decode, verify signature, validate claims, and check revocation of a JWT.

    Raises:
        TokenExpiredError: If token expiration (exp) is in the past.
        TokenRevokedError: If token jti is marked revoked in the revocation store.
        TokenInvalidError: If signature, algorithm, format, or required claims are invalid.
    """
    secret = get_jwt_secret_key()
    algorithm = get_jwt_algorithm()

    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["exp", "iat"]},
        )
    except ExpiredSignatureError as e:
        raise TokenExpiredError("Token has expired.") from e
    except (InvalidTokenError, PyJWTError) as e:
        raise TokenInvalidError(f"Invalid token: {e}") from e

    # Validate required claims
    for claim in REQUIRED_CLAIMS:
        if claim not in claims:
            raise TokenInvalidError(f"Token missing required claim: '{claim}'.")

    # Check revocation
    active_store = revocation_store or get_token_revocation_store()
    if active_store and active_store.is_revoked(claims["jti"]):
        raise TokenRevokedError("Token has been revoked.")

    return claims


__all__ = [
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenRevokedError",
    "create_access_token",
    "decode_access_token",
]
