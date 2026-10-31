"""
Security, Authentication, RBAC, Audit, and Rate Limiting for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from backend.arthlens.security.audit import AuditService, get_audit_service
from backend.arthlens.security.password import (
    PasswordValidationError,
    hash_password,
    validate_password_strength,
    verify_password,
)
from backend.arthlens.security.rate_limit import (
    InMemoryRateLimiter,
    PostgresRateLimiter,
    RateLimiter,
    get_rate_limiter,
    set_rate_limiter,
)
from backend.arthlens.security.rbac import (
    AuthenticatedUser,
    EndpointPolicy,
    EndpointPolicyRegistry,
    get_current_user,
    get_policy_registry,
    require_roles,
)
from backend.arthlens.security.revocation import (
    InMemoryTokenRevocationStore,
    PostgresTokenRevocationStore,
    TokenRevocationStore,
    get_token_revocation_store,
    set_token_revocation_store,
)
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import (
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    create_access_token,
    decode_access_token,
)

__all__ = [
    "Role",
    "PasswordValidationError",
    "validate_password_strength",
    "hash_password",
    "verify_password",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenRevokedError",
    "create_access_token",
    "decode_access_token",
    "TokenRevocationStore",
    "InMemoryTokenRevocationStore",
    "PostgresTokenRevocationStore",
    "get_token_revocation_store",
    "set_token_revocation_store",
    "AuditService",
    "get_audit_service",
    "RateLimiter",
    "InMemoryRateLimiter",
    "PostgresRateLimiter",
    "get_rate_limiter",
    "set_rate_limiter",
    "AuthenticatedUser",
    "EndpointPolicy",
    "EndpointPolicyRegistry",
    "get_policy_registry",
    "get_current_user",
    "require_roles",
]
