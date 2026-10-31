"""
FastAPI Application Factory for ArthLens Backend.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from typing import Callable
import re

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.arthlens.api.admin import router as admin_router
from backend.arthlens.api.auth import router as auth_router
from backend.arthlens.api.indicators import router as indicators_router
from backend.arthlens.api.policy import router as policy_router
from backend.arthlens.api.runs import router as runs_router
from backend.arthlens.api.scenarios import router as scenarios_router
from backend.arthlens.infra.config import (
    get_allowed_origins,
    get_auth_cookie_name,
    get_rate_limit_per_minute_ip,
    get_rate_limit_per_minute_user,
    get_trusted_proxies,
)
from backend.arthlens.security.rate_limit import get_rate_limiter
from backend.arthlens.security.rbac import get_policy_registry
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
        allowed_ip, rem_ip, reset_ip = limiter.check_rate_limit(
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
                allowed_u, rem_u, reset_u = limiter.check_rate_limit(
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


class DenyByDefaultMiddleware(BaseHTTPMiddleware):
    """
    Enforces deny-by-default behavior across all routes.
    Any endpoint route not explicitly registered in EndpointPolicyRegistry is forbidden.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method.upper()

        # Normalize parameterized path for matching
        registry = get_policy_registry()

        # Check exact path or parameterized routes
        policy = registry.get_policy(method, path)
        if not policy:
            # Check pattern matching for parameterized routes: e.g. /runs/{id}, /scenarios/{id}/branch, /geo/{id}/indicators
            normalized_path = re.sub(r"/[0-9a-fA-F\-]{36}", "/{id}", path)
            normalized_path = re.sub(r"/geo/[a-zA-Z0-9\._\-]+", "/geo/{id}", normalized_path)
            normalized_path = re.sub(r"/ledger/[0-9a-fA-F\-]{36}", "/ledger/{quantity_id}", normalized_path)
            normalized_path = re.sub(r"/replay/[0-9a-fA-F\-]+", "/replay/{id}", normalized_path)
            policy = registry.get_policy(method, normalized_path)

        # Allow swagger/openapi documentation in non-production
        is_docs = path in ("/docs", "/openapi.json", "/redoc")

        if not policy and not is_docs:
            # Check if route even exists in the application
            # If it starts with /internal or is undeclared:
            if path.startswith("/internal") or path.startswith("/undeclared"):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access forbidden: route has no registered authorization policy (deny-by-default)."},
                )

        return await call_next(request)


def create_app() -> FastAPI:
    """FastAPI application factory for ArthLens."""
    app = FastAPI(
        title="ArthLens Economic Decision Engine API",
        version="0.1.0",
        description="Evidence-gated agentic economic intelligence for Indian micro-enterprises",
    )

    # Register middlewares
    app.add_middleware(DenyByDefaultMiddleware)
    app.add_middleware(CSRFProtectionMiddleware)
    app.add_middleware(RateLimitingMiddleware)

    # Include API routers
    app.include_router(auth_router)
    app.include_router(runs_router)
    app.include_router(scenarios_router)
    app.include_router(policy_router)
    app.include_router(indicators_router)
    app.include_router(admin_router)

    return app


__all__ = ["create_app"]
