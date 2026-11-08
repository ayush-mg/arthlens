"""
Authentication Endpoints (/auth/login and /auth/logout).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
import threading
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from backend.arthlens.domain.repositories import UserAlreadyExistsError
from backend.arthlens.infra.config import (
    get_access_token_expire_minutes,
    get_auth_cookie_name,
    get_auth_cookie_samesite,
    get_auth_cookie_secure,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.email_service import is_dev_mode, send_password_reset_email
from backend.arthlens.security.password import (
    PasswordValidationError,
    hash_password,
    validate_password_strength,
    verify_password,
)
from backend.arthlens.security.rbac import AuthenticatedUser, get_current_user
from backend.arthlens.security.revocation import get_token_revocation_store
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$")

# In-memory single-use reset token store: token -> {"user_id": str, "exp": datetime}
_RESET_TOKENS: Dict[str, Dict[str, Any]] = {}
_RESET_LOCK = threading.Lock()


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the entrepreneur")
    email: str = Field(..., min_length=3, max_length=255, description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 characters)")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


class PasswordResetRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User email address")


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=16, description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


class LoginResponse(BaseModel):
    id: str
    email: str
    roles: List[str]
    full_name: Optional[str] = None
    access_token: Optional[str] = None
    token_type: str = "bearer"


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, response: Response, body: RegisterRequest) -> LoginResponse:
    """
    Public registration endpoint. Automatically assigns the ENTREPRENEUR role.
    Never allows registration as ADMIN or STEWARD.
    Establishes an authenticated HTTP-only session immediately upon creation.
    """
    clean_email = body.email.strip().lower()
    clean_name = body.full_name.strip()

    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )

    try:
        validate_password_strength(body.password)
    except PasswordValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    repo = PostgresUserRepository()
    audit = get_audit_service()
    client_ip = request.client.host if request.client else "127.0.0.1"

    pwd_hash = hash_password(body.password)
    try:
        user_id = repo.create_user({
            "email": clean_email,
            "password_hash": pwd_hash,
            "roles": [Role.ENTREPRENEUR.value],
            "quota_counters": {
                "full_name": clean_name,
                "is_active": True,
                "runs_today": 0,
                "cost_today": 0.0,
            },
        })
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # Issue session token
    token, jti = create_access_token(
        user_id=user_id,
        email=clean_email,
        roles=[Role.ENTREPRENEUR.value],
    )

    cookie_name = get_auth_cookie_name()
    expire_seconds = get_access_token_expire_minutes() * 60
    response.set_cookie(
        key=cookie_name,
        value=token,
        max_age=expire_seconds,
        httponly=True,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        path="/",
    )

    audit.record_event(
        actor=user_id,
        action="AUTH_REGISTER",
        target=f"user:{user_id}",
        payload={"email": clean_email, "role": Role.ENTREPRENEUR.value, "ip": client_ip},
    )

    return LoginResponse(
        id=user_id,
        email=clean_email,
        roles=[Role.ENTREPRENEUR.value],
        full_name=clean_name,
        access_token=token,
        token_type="bearer",
    )


@router.post("/login", response_model=LoginResponse)
def login(request: Request, response: Response, body: LoginRequest) -> LoginResponse:
    """
    Authenticate user credentials, record audit event, and establish session via HTTP-only cookie.
    Generic failure message is returned to prevent account enumeration.
    """
    repo = PostgresUserRepository()
    audit = get_audit_service()
    client_ip = request.client.host if request.client else "127.0.0.1"

    clean_email = body.email.strip().lower()
    user = repo.get_by_email(clean_email)

    if not user or not verify_password(body.password, user.get("password_hash", "")):
        audit.record_event(
            actor=None,
            action="AUTH_LOGIN_FAILURE",
            target=f"email:{clean_email}",
            payload={"ip": client_ip, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Check whether the account is deactivated
    quota_counters = user.get("quota_counters") or {}
    if quota_counters.get("is_active") is False:
        audit.record_event(
            actor=user["id"],
            action="AUTH_LOGIN_DEACTIVATED",
            target=f"user:{user['id']}",
            payload={"ip": client_ip},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact an administrator.",
        )

    # Establish authenticated session
    roles = user.get("roles") or []
    token, jti = create_access_token(
        user_id=user["id"],
        email=user["email"],
        roles=roles,
    )

    cookie_name = get_auth_cookie_name()
    expire_seconds = get_access_token_expire_minutes() * 60
    response.set_cookie(
        key=cookie_name,
        value=token,
        max_age=expire_seconds,
        httponly=True,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        path="/",
    )

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
        full_name=quota_counters.get("full_name"),
        access_token=token,
        token_type="bearer",
    )


@router.post("/password-reset/request")
def request_password_reset(body: PasswordResetRequest) -> Dict[str, Any]:
    """
    Initiate password recovery. Generates an expiring single-use reset token.
    Persists token hash in database, dispatches via configurable SMTP email provider,
    and returns a clearly labeled recovery token in local development mode.
    Never exposes whether the email address has an active account.
    """
    clean_email = body.email.strip().lower()
    repo = PostgresUserRepository()
    user = repo.get_by_email(clean_email)

    dev_token: Optional[str] = None
    dev_url: Optional[str] = None

    if user and user.get("quota_counters", {}).get("is_active", True) is not False:
        reset_token = secrets.token_urlsafe(32)
        exp = datetime.now(timezone.utc) + timedelta(minutes=15)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

        # 1. Persist token hash in authoritative user repository
        repo.set_password_reset_token(user["id"], token_hash, exp)

        # 2. Maintain thread-safe in-memory cache
        with _RESET_LOCK:
            _RESET_TOKENS[reset_token] = {
                "user_id": user["id"],
                "exp": exp,
            }

        # 3. Audit trail
        audit = get_audit_service()
        audit.record_event(
            actor=user["id"],
            action="AUTH_PASSWORD_RESET_REQUEST",
            target=f"user:{user['id']}",
            payload={"exp": exp.isoformat()},
        )

        # 4. Dispatch via configured email provider (or local dev console logger)
        send_password_reset_email(clean_email, reset_token)

        if is_dev_mode():
            dev_token = reset_token
            dev_url = f"http://localhost:3000/reset-password?token={reset_token}"

    response_payload: Dict[str, Any] = {
        "status": "ok",
        "message": "If an account exists with this email, password recovery instructions have been sent.",
    }
    if dev_token and dev_url:
        response_payload["dev_recovery_token"] = dev_token
        response_payload["dev_recovery_url"] = dev_url

    return response_payload


@router.post("/password-reset/confirm")
def confirm_password_reset(body: PasswordResetConfirm) -> Dict[str, str]:
    """
    Redeem single-use password reset token, update credentials, and invalidate prior active sessions.
    """
    try:
        validate_password_strength(body.new_password)
    except PasswordValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    clean_token = body.token.strip()
    token_hash = hashlib.sha256(clean_token.encode()).hexdigest()
    pwd_hash = hash_password(body.new_password)
    repo = PostgresUserRepository()

    # 1. Authoritative verification and consumption in repository
    user_record = repo.verify_and_consume_password_reset(token_hash, pwd_hash)

    # 2. In-memory fallback if not consumed via repository
    if not user_record:
        with _RESET_LOCK:
            mem_record = _RESET_TOKENS.pop(clean_token, None)
        if mem_record and mem_record["exp"] >= datetime.now(timezone.utc):
            success = repo.update_password(mem_record["user_id"], pwd_hash)
            if success:
                user_record = {"id": mem_record["user_id"]}

    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid, expired, or already used.",
        )

    # Invalidate in-memory tokens if present
    with _RESET_LOCK:
        _RESET_TOKENS.pop(clean_token, None)

    audit = get_audit_service()
    audit.record_event(
        actor=user_record["id"],
        action="AUTH_PASSWORD_RESET_SUCCESS",
        target=f"user:{user_record['id']}",
        payload={},
    )

    return {"status": "ok", "message": "Password has been successfully updated. Prior sessions invalidated. Please log in."}


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


@router.get("/me", response_model=LoginResponse)
def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LoginResponse:
    """Retrieve authenticated user context and roles from session token."""
    return LoginResponse(
        id=current_user.id,
        email=current_user.email,
        roles=list(current_user.roles),
    )
