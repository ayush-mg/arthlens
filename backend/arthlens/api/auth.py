"""
Authentication Endpoints (/auth/login and /auth/logout).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from backend.arthlens.infra.config import (
    get_access_token_expire_minutes,
    get_auth_cookie_name,
    get_auth_cookie_samesite,
    get_auth_cookie_secure,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.password import verify_password
from backend.arthlens.security.revocation import get_token_revocation_store
from backend.arthlens.security.tokens import create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


class LoginResponse(BaseModel):
    id: str
    email: str
    roles: List[str]


@router.post("/login", response_model=LoginResponse)
def login(request: Request, response: Response, body: LoginRequest) -> LoginResponse:
    """
    Authenticate user credentials, record audit event, and establish session via HTTP-only cookie.
    Generic failure message is returned to prevent account enumeration.
    """
    repo = PostgresUserRepository()
    audit = get_audit_service()
    client_ip = request.client.host if request.client else "127.0.0.1"

    user = repo.get_by_email(body.email.strip().lower())

    if not user or not verify_password(body.password, user.get("password_hash", "")):
        # Record failed login attempt for audit trail (sanitized)
        audit.record_event(
            actor=None,
            action="AUTH_LOGIN_FAILURE",
            target=f"email:{body.email.strip().lower()}",
            payload={"ip": client_ip, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Establish authenticated session
    roles = user.get("roles") or []
    token, jti = create_access_token(
        user_id=user["id"],
        email=user["email"],
        roles=roles,
    )

    # Configure secure HTTP-only cookie
    cookie_name = get_auth_cookie_name()
    expire_seconds = get_access_token_expire_minutes() * 60
    secure_flag = get_auth_cookie_secure()
    samesite_attr = get_auth_cookie_samesite()

    response.set_cookie(
        key=cookie_name,
        value=token,
        max_age=expire_seconds,
        httponly=True,
        secure=secure_flag,
        samesite=samesite_attr,
        path="/",
    )

    # Record successful login audit event
    audit.record_event(
        actor=user["id"],
        action="AUTH_LOGIN_SUCCESS",
        target=f"user:{user['id']}",
        payload={"ip": client_ip, "jti": jti},
    )

    return LoginResponse(
        id=user["id"],
        email=user["email"],
        roles=roles,
    )


@router.post("/logout")
def logout(request: Request, response: Response) -> Dict[str, str]:
    """
    Invalidate session: revoke token JTI in revocation store and delete session cookie.
    """
    cookie_name = get_auth_cookie_name()
    token = request.cookies.get(cookie_name)
    audit = get_audit_service()
    revocation = get_token_revocation_store()

    if token:
        try:
            claims = decode_access_token(token)
            jti = claims["jti"]
            exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
            revocation.revoke(jti, exp)
            audit.record_event(
                actor=claims["sub"],
                action="AUTH_LOGOUT",
                target=f"user:{claims['sub']}",
                payload={"jti": jti},
            )
        except Exception:
            pass

    # Clear cookie
    response.delete_cookie(
        key=cookie_name,
        httponly=True,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        path="/",
    )
    return {"status": "logged_out"}


@router.get("/ping")
def ping() -> Dict[str, str]:
    """Unauthenticated health ping endpoint."""
    return {"status": "pong"}
