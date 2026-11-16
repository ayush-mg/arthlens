"""
FastAPI Application Factory for ArthLens Backend.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

import hmac
import re
from typing import Any, Callable, Tuple

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from starlette.routing import Match

from backend.arthlens.api.admin import router as admin_router
from backend.arthlens.api.auth import router as auth_router
from backend.arthlens.api.business import router as business_router
from backend.arthlens.infra.config import (
    get_allowed_origins,
    get_auth_cookie_name,
    get_environment,
    get_rate_limit_per_minute_ip,
    get_rate_limit_per_minute_user,
    get_trusted_proxies,
)
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.security.rate_limit import get_rate_limiter
from backend.arthlens.security.tokens import (
    decode_access_token,
    TokenExpiredError,
    TokenRevokedError,
    TokenInvalidError,
)
from backend.arthlens.security.rbac import get_policy_registry, get_user_repository, EndpointPolicy
from backend.arthlens.domain.business import BusinessRole
from backend.arthlens.security.roles import Role
from backend.arthlens.infra.business_repositories import PostgresBusinessRepository
import uuid

from backend.arthlens.security.tokens import decode_access_token


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Concurrency-safe distributed rate limiting middleware.
    Enforces per-IP and per-User sliding limits across all incoming requests.
    Validates reverse-proxy trust before accepting forwarded client IPs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        limiter = get_rate_limiter()

        # 1. Resolve client IP: only trust X-Forwarded-For if caller is a configured trusted proxy
        trusted_proxies = get_trusted_proxies()
        direct_ip = request.client.host if request.client else "127.0.0.1"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded and direct_ip in trusted_proxies:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = direct_ip

        # Check per-IP rate limit
        ip_limit = get_rate_limit_per_minute_ip()
        allowed_ip, _, reset_ip = limiter.check_rate_limit(
            key=f"ip:{client_ip}",
            limit=ip_limit,
            window_seconds=60,
        )
        if not allowed_ip:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests from this IP address. Please slow down."},
                headers={"Retry-After": str(reset_ip)},
            )

        # 2. Check per-User rate limit if user session cookie is present
        cookie_name = get_auth_cookie_name()
        token = request.cookies.get(cookie_name)
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()

        if token:
            try:
                claims = decode_access_token(token)
                user_id = claims["sub"]
                user_limit = get_rate_limit_per_minute_user()
                allowed_u, _, reset_u = limiter.check_rate_limit(
                    key=f"user:{user_id}",
                    limit=user_limit,
                    window_seconds=60,
                )
                if not allowed_u:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "User rate limit exceeded."},
                        headers={"Retry-After": str(reset_u)},
                    )
            except Exception:
                pass

        return await call_next(request)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Defense-in-Depth Middleware.
    Validates Origin and Sec-Fetch-Site headers on state-changing requests (POST, PUT, PATCH, DELETE)
    when authentication relies on ambient session cookies.
    Requests using Authorization: Bearer <token> headers are immune to CSRF and exempt.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            cookie_name = get_auth_cookie_name()
            has_cookie = cookie_name in request.cookies
            has_bearer = bool(request.headers.get("Authorization", "").startswith("Bearer "))

            # Enforce CSRF validation if request relies on cookie auth without Bearer
            if has_cookie and not has_bearer:
                csrf_cookie = request.cookies.get("arthlens_csrf")
                csrf_header = request.headers.get("X-CSRF-Token")
                if csrf_cookie and (not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header)):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "CSRF token is missing or invalid."},
                    )
                fetch_site = request.headers.get("Sec-Fetch-Site")
                if fetch_site in ("cross-site",):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Cross-origin request blocked by CSRF policy."},
                    )

                origin = request.headers.get("Origin")
                if origin:
                    allowed = get_allowed_origins()
                    host = request.headers.get("Host", "")
                    matches_allowed = origin in allowed or any(origin.endswith(a.replace("http://", "").replace("https://", "")) for a in allowed)
                    matches_host = host and (origin in (f"http://{host}", f"https://{host}"))
                    if not (matches_allowed or matches_host):
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={"detail": "Forbidden: Untrusted Origin."},
                        )

        return await call_next(request)


def _match_route(routes: Any, scope: dict) -> Tuple[Match, Any]:
    """
    Recursively tests Starlette / FastAPI routes against the incoming request scope.
    Returns (Match.FULL, route) if path and method match,
    (Match.PARTIAL, route) if path matches but method does not,
    or (Match.NONE, None) if route does not exist.
    """
    best_match = Match.NONE
    matched_route = None
    for r in routes:
        if hasattr(r, "routes"):
            m, route_found = _match_route(r.routes, scope)
            if m == Match.FULL:
                return m, route_found
            elif m == Match.PARTIAL and best_match != Match.FULL:
                best_match = Match.PARTIAL
                matched_route = route_found
        elif hasattr(r, "original_router"):
            m, route_found = _match_route(r.original_router.routes, scope)
            if m == Match.FULL:
                return m, route_found
            elif m == Match.PARTIAL and best_match != Match.FULL:
                best_match = Match.PARTIAL
                matched_route = route_found
        elif hasattr(r, "matches"):
            m, _ = r.matches(scope)
            if m == Match.FULL:
                return m, r
            elif m == Match.PARTIAL and best_match != Match.FULL:
                best_match = Match.PARTIAL
                matched_route = r
    return best_match, matched_route


def _check_auth_and_ownership(token: str, policy: EndpointPolicy, path: str) -> Any:
    """Synchronous authentication and authorization verification running in threadpool."""
    try:
        claims = decode_access_token(token)
    except TokenExpiredError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication session expired. Please log in again."},
        )
    except TokenRevokedError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Session has been revoked upon logout."},
        )
    except TokenInvalidError as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": f"Invalid authentication credentials: {e}"},
        )

    if claims.get("token_type", "access") != "access":
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Refresh credentials cannot be used as API access tokens."},
        )
    user_id = claims.get("sub")
    if not user_id:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid token subject."},
        )

    # Re-verify user existence and active status in database
    user_repo = get_user_repository()
    user_record = user_repo.get_by_id(user_id)
    if not user_record:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "User account no longer exists."},
        )

    quota = user_record.get("quota_counters") or {}
    if quota.get("is_active") is False:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "User account has been deactivated."},
        )

    user_roles = set(user_record.get("roles") or [])
    is_admin = Role.ADMIN.value in user_roles

    # System Role Enforcement
    system_roles = {r.value for r in Role}
    req_system_roles = policy.allowed_roles & system_roles
    if req_system_roles and not (is_admin and policy.allow_admin_bypass):
        if not (user_roles & req_system_roles):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access forbidden: required role not held."},
            )

    # Tenant Scoping & Ownership Enforcement for /businesses/{business_id}
    biz_match = re.search(r"/businesses/([0-9a-fA-F\-]{36})", path)
    if biz_match:
        try:
            biz_uuid = uuid.UUID(biz_match.group(1))
            user_uuid = uuid.UUID(str(user_id))
            biz_repo = PostgresBusinessRepository()
            biz = biz_repo.get_by_id(biz_uuid)
            if not biz:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Business workspace {biz_uuid} not found."},
                )

            is_owner = str(biz.owner_id) == str(user_uuid)
            membership = biz_repo.get_membership(biz_uuid, user_uuid)
            is_member = bool(membership and membership.is_active)

            admin_bypass = is_admin and policy.allow_admin_bypass
            if not is_owner and not is_member and not admin_bypass:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied: you do not have permission to access this business workspace."},
                )

            if policy.require_ownership and not is_owner and not admin_bypass:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Ownership required for this operation."},
                )

        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid tenant or user identity in authorization context."},
            )

    return None


class DenyByDefaultMiddleware(BaseHTTPMiddleware):
    """
    Enforces deny-by-default behavior across all routes.
    Blocks undeclared internal or unrouted debug paths, enforces active route registration
    and authorization policies against the FastAPI route table, and rejects un-policied routes.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method.upper()

        # 1. Allow CORS preflight requests
        if method == "OPTIONS":
            return await call_next(request)

        # 2. Block documentation paths in production; permit in development/test
        is_docs = path in ("/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect")
        if is_docs:
            if get_environment() == "production":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": "Not Found"},
                )
            return await call_next(request)

        # 3. Explicitly deny private, internal, or undeclared route prefixes
        if path.startswith(("/internal", "/undeclared", "/private", "/secret")):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access forbidden: route has no registered authorization policy (deny-by-default)."},
            )

        # 4. Check route existence against FastAPI route table
        match_type, matched_route = _match_route(request.app.routes, request.scope)

        # If trailing slash causes NONE, check if canonical path matches to allow framework redirect
        if match_type == Match.NONE and path.endswith("/") and len(path) > 1:
            alt_match_type, _ = _match_route(
                request.app.routes,
                dict(request.scope, path=path.rstrip("/")),
            )
            if alt_match_type in (Match.FULL, Match.PARTIAL):
                return await call_next(request)

        if match_type == Match.NONE:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )

        if match_type == Match.PARTIAL:
            return JSONResponse(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                content={"detail": "Method Not Allowed"},
            )

        # 5. Route matches: verify registered policy in EndpointPolicyRegistry (FAIL CLOSED)
        registry = get_policy_registry()
        route_path = getattr(matched_route, "path", path)
        norm_route_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "{id}", route_path)
        norm_url_path = re.sub(r"/[0-9a-fA-F\-]{36}", "/{id}", path)
        lookup_path = norm_url_path.rstrip("/") if len(norm_url_path) > 1 else norm_url_path

        policy = (
            registry.get_policy(method, norm_route_path)
            or registry.get_policy(method, route_path)
            or registry.get_policy(method, lookup_path)
            or registry.get_policy(method, norm_url_path)
            or registry.get_policy(method, path)
        )

        if not policy:
            # Route exists in FastAPI table but has no registered authorization policy -> Reject
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access forbidden: route has no registered authorization policy (deny-by-default)."},
            )

        # 6. ENFORCE AUTHENTICATION, ROLES & TENANT OWNERSHIP PERMISSIONS IN MIDDLEWARE (Audit Item 1)
        if "*" not in policy.allowed_roles:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            else:
                cookie_name = get_auth_cookie_name()
                token = request.cookies.get(cookie_name)

            if not token:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required. Missing session cookie or Bearer header."},
                )

            auth_error = await run_in_threadpool(_check_auth_and_ownership, token, policy, path)
            if auth_error is not None:
                return auth_error

        return await call_next(request)


def create_app() -> FastAPI:
    """FastAPI application factory for ArthLens."""
    app = FastAPI(
        title="ArthLens Business Operating System & Decision Intelligence Platform API",
        version="1.0.0",
        description="Authoritative Business Operating System, Deterministic Financial Intelligence, Decision Intelligence Engine, and Gemini-Powered Business Copilot API.",
    )

    # Register middlewares
    app.add_middleware(DenyByDefaultMiddleware)
    app.add_middleware(CSRFProtectionMiddleware)
    app.add_middleware(RateLimitingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include active ArthLens Business OS & Decision Intelligence routers
    app.include_router(auth_router)
    app.include_router(business_router)
    app.include_router(admin_router)

    @app.get("/health", tags=["Health"])
    @app.get("/api/v1/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """Unauthenticated health check endpoint for deployment monitoring."""
        return {"status": "healthy", "service": "arthlens-backend"}

    @app.get("/health/live", tags=["Health"])
    def health_live() -> dict[str, str]:
        """Liveness probe that does not depend on downstream services."""
        return {"status": "live", "service": "arthlens-backend"}

    @app.get("/health/ready", tags=["Health"])
    def health_ready() -> dict[str, str]:
        """Readiness probe that confirms the application can reach PostgreSQL."""
        from fastapi import HTTPException

        try:
            with get_session_factory()() as session:
                session.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not ready.") from exc
        return {"status": "ready", "service": "arthlens-backend"}

    return app


__all__ = ["create_app"]
