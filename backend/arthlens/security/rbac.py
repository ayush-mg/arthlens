"""
Role-Based Access Control (RBAC), Permission Matrix, and Authentication Dependencies.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Set, Tuple, Union

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
        """Register the authoritative ArthLens Business OS & Decision Platform permission matrix."""
        # 1. Public or Session endpoints
        self.register("/auth/login", "POST", allowed_roles={"*"})
        self.register("/auth/login/initiate", "POST", allowed_roles={"*"})
        self.register("/auth/login/verify-otp", "POST", allowed_roles={"*"})
        self.register("/auth/register", "POST", allowed_roles={"*"})
        self.register("/auth/register/initiate", "POST", allowed_roles={"*"})
        self.register("/auth/register/verify-otp", "POST", allowed_roles={"*"})
        self.register("/auth/otp/resend", "POST", allowed_roles={"*"})
        self.register("/auth/google", "POST", allowed_roles={"*"})
        self.register("/auth/refresh", "POST", allowed_roles={"*"})
        self.register("/auth/logout", "POST", allowed_roles={"*"})
        self.register("/auth/ping", "GET", allowed_roles={"*"})
        self.register("/health", "GET", allowed_roles={"*"})
        self.register("/api/v1/health", "GET", allowed_roles={"*"})
        self.register("/auth/me", "GET", allowed_roles={"*"})
        self.register("/auth/password-reset/request", "POST", allowed_roles={"*"})
        self.register("/auth/password-reset/confirm", "POST", allowed_roles={"*"})
        # Unauthenticated probes used by the load balancer and deployment smoke suite.
        self.register("/health/live", "GET", allowed_roles={"*"})
        self.register("/health/ready", "GET", allowed_roles={"*"})

        # 2. Business Operating System & Decision Intelligence endpoints
        biz_roles = {Role.ENTREPRENEUR.value, Role.ADMIN.value}
        self.register("/businesses", "GET", allowed_roles=biz_roles)
        self.register("/businesses", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}", "PUT", allowed_roles=biz_roles)
        self.register("/businesses/{id}", "DELETE", allowed_roles=biz_roles, require_ownership=True)
        self.register("/businesses/{id}/archive", "POST", allowed_roles=biz_roles, require_ownership=True)
        self.register("/businesses/{id}/members", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/members", "POST", allowed_roles=biz_roles, require_ownership=True)
        self.register("/businesses/{id}/members/{id}", "PATCH", allowed_roles=biz_roles, require_ownership=True)
        self.register("/businesses/{id}/members/{id}", "DELETE", allowed_roles=biz_roles, require_ownership=True)
        self.register("/businesses/{id}/activity", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/khata/reconcile", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/customers", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/customers", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/customers/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/customers/{id}", "PUT", allowed_roles=biz_roles)
        self.register("/businesses/{id}/customers/{id}/ledger", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/suppliers", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/suppliers", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/suppliers/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/suppliers/{id}", "PUT", allowed_roles=biz_roles)
        self.register("/businesses/{id}/suppliers/{id}/ledger", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/products", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/products", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/products/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/products/{id}", "PUT", allowed_roles=biz_roles)
        self.register("/businesses/{id}/inventory/adjust", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/inventory/balances", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/inventory/movements", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/inventory/unreconciled-costs", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/inventory/reconcile-costs", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/inventory/cost-reconciliation-history", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices/{id}", "PUT", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices/{id}", "DELETE", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices/{id}/payments", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices/{id}/cancel", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/invoices/{id}/pdf", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/purchases", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/purchases", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/purchases/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/purchases/{id}", "PUT", allowed_roles=biz_roles)
        self.register("/businesses/{id}/purchases/{id}", "DELETE", allowed_roles=biz_roles)
        self.register("/businesses/{id}/purchases/{id}/payments", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/purchases/{id}/pdf", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/income", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/income", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/expenses", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/expenses", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/cash-position", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}", "PUT", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}", "DELETE", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/recalculate", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/evaluate", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/milestones", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/milestones", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/milestones/{id}", "DELETE", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/plans", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/plans", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/tasks", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/tasks", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/tasks/{id}", "PATCH", allowed_roles=biz_roles)
        self.register("/businesses/{id}/goals/{id}/tasks/{id}", "DELETE", allowed_roles=biz_roles)
        self.register("/businesses/{id}/analytics/pnl", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/analytics/cash-flow", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/analytics/working-capital", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/analytics/ageing", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/analytics/break-even", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/analytics/health-score", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/decisions/evaluate", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/decisions/simulate-risk", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/decisions/sensitivity", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/decisions/history", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/decisions/{id}/versions", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/agent/investigate", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/agent/sessions/{id}/actions", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/agent/sessions/{id}/actions", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/agent/sessions/{id}/actions/{id}/confirm", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/agent/sessions/{id}/actions/{id}/reject", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/agent/sessions/{id}/actions/{id}/download", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios/{id}", "DELETE", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios/compare", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios/{id}/versions", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios/{id}/versions", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios/{id}/runs", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios/{id}/runs", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/scenarios/{id}/runs/{id}/replay", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/reports/dossier.pdf", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/reports/decisions/{id}/brief.pdf", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/reports/customers/{id}/ledger.csv", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/reports/suppliers/{id}/ledger.csv", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/reports/ledger.csv", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/ledger/journal-entries", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/ledger/trial-balance", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/ledger/accounts/{id}", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/periods", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/periods", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/periods/{id}/close", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/returns/sales", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/returns/purchases", "POST", allowed_roles=biz_roles)
        self.register("/businesses/{id}/transactions", "GET", allowed_roles=biz_roles)
        self.register("/businesses/{id}/transactions/export.csv", "GET", allowed_roles=biz_roles)

        # 3. Administrative endpoints
        self.register("/admin/users", "GET", allowed_roles={Role.ADMIN.value})
        self.register("/admin/users/{id}/role", "POST", allowed_roles={Role.ADMIN.value})
        self.register("/admin/users/{id}/deactivate", "POST", allowed_roles={Role.ADMIN.value})
        self.register("/admin/users/{id}/activate", "POST", allowed_roles={Role.ADMIN.value})
        self.register("/admin/audit", "GET", allowed_roles={Role.ADMIN.value})
        self.register("/admin/audit-events", "GET", allowed_roles={Role.ADMIN.value})
        self.register("/admin/sources", "GET", allowed_roles={Role.ADMIN.value})

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
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    else:
        cookie_name = get_auth_cookie_name()
        token = request.cookies.get(cookie_name)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing session cookie or Bearer header.",
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

    if claims.get("token_type", "access") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh credentials cannot be used as API access tokens.",
        )
    user_id = claims["sub"]

    # Re-validate user existence and authoritative roles from repository (FAIL CLOSED)
    try:
        repo = get_user_repository()
        user_record = repo.get_by_id(user_id)
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists.",
            )

        quota_counters = user_record.get("quota_counters") or {}
        if quota_counters.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account has been deactivated.",
            )

        token_valid_after_str = quota_counters.get("token_valid_after")
        if token_valid_after_str:
            try:
                tva_ts = datetime.fromisoformat(token_valid_after_str).timestamp()
                token_iat = claims.get("iat")
                if token_iat is not None:
                    # Compare float timestamps (microsecond resolution) to prevent race conditions
                    # where newly issued tokens immediately after reset are wrongly invalidated
                    if float(token_iat) < tva_ts:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Session has been revoked due to a security update. Please log in again.",
                        )
            except HTTPException:
                raise
            except Exception:
                pass

        fresh_roles = tuple(user_record.get("roles") or [])
        fresh_email = user_record.get("email") or claims.get("email", "")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authoritative user verification failed: {exc}",
        )

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
