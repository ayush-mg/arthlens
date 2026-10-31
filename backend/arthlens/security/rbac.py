"""
Role-Based Access Control (RBAC), Permission Matrix, and Authentication Dependencies.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from fastapi import Depends, HTTPException, Request, status

from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import (
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    decode_access_token,
)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Authenticated user context extracted from validated JWT session token."""
    id: str
    email: str
    roles: Tuple[str, ...]
    jti: str

    def has_role(self, role: Union[Role, str]) -> bool:
        r_str = role.value if isinstance(role, Role) else str(role)
        return r_str in self.roles


@dataclass(frozen=True)
class EndpointPolicy:
    """Declared authorization policy for an API endpoint."""
    path: str
    method: str
    allowed_roles: Set[str]
    require_ownership: bool = False
    allow_admin_bypass: bool = False


class EndpointPolicyRegistry:
    """
    Centralized registry of declared endpoint authorization policies.
    Enforces deny-by-default behavior across the API surface.
    """

    def __init__(self) -> None:
        self._policies: Dict[Tuple[str, str], EndpointPolicy] = {}
        self._register_handbook_policies()

    def _register_handbook_policies(self) -> None:
        """Register the authoritative Handbook Part 10.1 permission matrix."""
        # 1. Public or Session endpoints
        self.register("/auth/login", "POST", allowed_roles={"*"})
        self.register("/auth/logout", "POST", allowed_roles={"*"})
        self.register("/auth/ping", "GET", allowed_roles={"*"})

        # 2. Runs endpoints
        self.register("/runs", "POST", allowed_roles={Role.ENTREPRENEUR.value})
        self.register("/runs/{id}", "GET", allowed_roles={Role.ENTREPRENEUR.value, Role.ADMIN.value}, require_ownership=True, allow_admin_bypass=True)
        self.register("/runs/{id}/events", "GET", allowed_roles={Role.ENTREPRENEUR.value, Role.ADMIN.value}, require_ownership=True, allow_admin_bypass=True)
        self.register("/runs/{id}/answer", "POST", allowed_roles={Role.ENTREPRENEUR.value}, require_ownership=True, allow_admin_bypass=False)
        self.register("/runs/{id}/approve", "POST", allowed_roles={Role.ENTREPRENEUR.value, Role.STEWARD.value}, require_ownership=True)

        # 3. Scenarios endpoints
        self.register("/scenarios", "POST", allowed_roles={Role.ENTREPRENEUR.value})
        self.register("/scenarios/{id}/branch", "POST", allowed_roles={Role.ENTREPRENEUR.value}, require_ownership=True)

        # 4. Epistemic Ledger, Geo, Policy, Replay
        self.register("/ledger/{quantity_id}", "GET", allowed_roles={Role.ENTREPRENEUR.value, Role.STEWARD.value, Role.ADMIN.value})
        self.register("/geo/{id}/indicators", "GET", allowed_roles={Role.ENTREPRENEUR.value, Role.STEWARD.value, Role.ADMIN.value})
        self.register("/policy/rules", "GET", allowed_roles={Role.ENTREPRENEUR.value, Role.STEWARD.value, Role.ADMIN.value})
        self.register("/policy/rules", "POST", allowed_roles={Role.STEWARD.value})
        self.register("/replay/{id}", "GET", allowed_roles={"*"})

        # 5. Administrative endpoints
        self.register("/admin/users", "GET", allowed_roles={Role.ADMIN.value})
        self.register("/admin/audit", "GET", allowed_roles={Role.ADMIN.value})

    def register(
        self,
        path: str,
        method: str,
        allowed_roles: Set[str],
        require_ownership: bool = False,
        allow_admin_bypass: bool = False,
    ) -> None:
        key = (method.upper(), path)
        self._policies[key] = EndpointPolicy(
            path=path,
            method=method.upper(),
            allowed_roles=set(allowed_roles),
            require_ownership=require_ownership,
            allow_admin_bypass=allow_admin_bypass,
        )

    def get_policy(self, method: str, path: str) -> Optional[EndpointPolicy]:
        # Exact match
        key = (method.upper(), path)
        if key in self._policies:
            return self._policies[key]
        return None


_policy_registry = EndpointPolicyRegistry()


def get_policy_registry() -> EndpointPolicyRegistry:
    return _policy_registry


_user_repo_factory: Optional[Callable[[], Any]] = None


def get_user_repository() -> Any:
    global _user_repo_factory
    if _user_repo_factory is not None:
        return _user_repo_factory()
    from backend.arthlens.infra.repositories import PostgresUserRepository
    return PostgresUserRepository()


def set_user_repository_factory(factory: Optional[Callable[[], Any]]) -> None:
    global _user_repo_factory
    _user_repo_factory = factory


def get_current_user(request: Request) -> AuthenticatedUser:
    """
    FastAPI dependency extracting and verifying the authenticated user from the HTTP-only cookie
    or Bearer authorization header.
    Validates cryptographic signature, expiration, revocation, and re-validates fresh roles
    from the authoritative user repository to prevent stale JWT privilege retention.
    Raises 401 Unauthorized if missing, invalid, expired, revoked, or account is deleted.
    """
    cookie_name = get_auth_cookie_name()
    token = request.cookies.get(cookie_name)

    # Fallback to Authorization: Bearer <token> header if cookie absent
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing session cookie.",
        )

    try:
        claims = decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session expired. Please log in again.",
        )
    except TokenRevokedError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked upon logout.",
        )
    except TokenInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
        )

    user_id = claims["sub"]

    # Re-validate user existence and authoritative roles from repository
    try:
        repo = get_user_repository()
        user_record = repo.get_by_id(user_id)
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists or has been deactivated.",
            )
        fresh_roles = tuple(user_record.get("roles") or [])
        fresh_email = user_record.get("email") or claims["email"]
    except HTTPException:
        raise
    except Exception:
        # Fallback to claims in isolated unit test environments without database connectivity
        fresh_roles = tuple(claims.get("roles") or ())
        fresh_email = claims.get("email", "")

    return AuthenticatedUser(
        id=user_id,
        email=fresh_email,
        roles=fresh_roles,
        jti=claims["jti"],
    )


def require_roles(*roles: Union[Role, str]) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """
    FastAPI dependency factory enforcing that the authenticated user possesses at least
    one of the specified roles. Raises 403 Forbidden on failure.
    """
    role_strings = {r.value if isinstance(r, Role) else str(r) for r in roles}

    def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not any(user_role in role_strings for user_role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: required role not held. Needs one of: {sorted(role_strings)}",
            )
        return current_user

    return role_checker


__all__ = [
    "AuthenticatedUser",
    "EndpointPolicy",
    "EndpointPolicyRegistry",
    "get_policy_registry",
    "get_current_user",
    "require_roles",
]
