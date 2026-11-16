"""
Authentication Endpoints (/auth/login and /auth/logout).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlencode
from urllib.request import urlopen
import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from backend.arthlens.domain.repositories import UserAlreadyExistsError
from backend.arthlens.infra.config import (
    get_access_token_expire_minutes,
    get_auth_cookie_name,
    get_auth_cookie_samesite,
    get_auth_cookie_secure,
    get_google_client_ids,
    get_google_jwks_client,
    get_jwt_secret_key,
    is_test_environment,
    is_production_environment,
)
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import AuthOtpChallengeModel, UserModel
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.email_service import is_dev_mode, send_email_otp, send_password_reset_email
from backend.arthlens.security.password import (
    PasswordValidationError,
    hash_password,
    validate_password_strength,
    verify_password,
)
from backend.arthlens.security.rbac import AuthenticatedUser, get_current_user
from backend.arthlens.security.revocation import get_token_revocation_store
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import (
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$")

# In-memory single-use reset token store: token -> {"user_id": str, "exp": datetime}
_RESET_TOKENS: Dict[str, Dict[str, Any]] = {}
_RESET_LOCK = threading.Lock()
REFRESH_COOKIE_SUFFIX = "_refresh"
CSRF_COOKIE_NAME = "arthlens_csrf"


def _set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_name = get_auth_cookie_name()
    response.set_cookie(
        key=cookie_name,
        value=access_token,
        max_age=get_access_token_expire_minutes() * 60,
        httponly=True,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        path="/",
    )
    response.set_cookie(
        key=f"{cookie_name}{REFRESH_COOKIE_SUFFIX}",
        value=refresh_token,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        path="/auth",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(32),
        max_age=30 * 24 * 60 * 60,
        httponly=False,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        path="/",
    )


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the entrepreneur")
    email: str = Field(..., min_length=3, max_length=255, description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 characters)")
    role: Optional[str] = None  # Accepted for client compatibility; public registration never assigns it.


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


class OtpVerificationRequest(BaseModel):
    challenge_id: uuid.UUID
    email: str = Field(..., min_length=3, max_length=320)
    otp_code: str = Field(..., pattern=r"^\d{6}$")


class OtpResendRequest(BaseModel):
    challenge_id: uuid.UUID
    email: str = Field(..., min_length=3, max_length=320)


class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = None
    mode: Literal["login", "register"]
    email: Optional[str] = None
    full_name: Optional[str] = None


def _legacy_auth_bypass(request: Request) -> bool:
    """Keep the historic token-returning endpoints for tests/local fixtures only."""
    if is_test_environment():
        return True
    return (
        is_dev_mode()
        and request.headers.get("X-Test-Bypass-OTP", "").strip().lower() == "true"
    )


def _otp_hash(challenge_id: uuid.UUID, email: str, purpose: str, code: str) -> str:
    message = f"{challenge_id}:{email.strip().lower()}:{purpose}:{code}".encode("utf-8")
    return hmac.new(get_jwt_secret_key().encode("utf-8"), message, hashlib.sha256).hexdigest()


def _new_otp_challenge(user_id: Optional[str], email: str, purpose: str) -> Dict[str, Any]:
    clean_email = email.strip().lower()
    challenge_id = uuid.uuid4()
    code = f"{secrets.randbelow(900_000) + 100_000:06d}"
    now = datetime.now(timezone.utc)
    factory = get_session_factory()
    with factory() as session, session.begin():
        session.execute(
            update(AuthOtpChallengeModel)
            .where(
                AuthOtpChallengeModel.email == clean_email,
                AuthOtpChallengeModel.purpose == purpose,
                AuthOtpChallengeModel.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        session.add(AuthOtpChallengeModel(
            id=challenge_id,
            user_id=uuid.UUID(user_id) if user_id else None,
            email=clean_email,
            purpose=purpose,
            code_hash=_otp_hash(challenge_id, clean_email, purpose, code),
            attempts=0,
            max_attempts=5,
            expires_at=now + timedelta(minutes=10),
        ))

    try:
        _sent, delivery_method = send_email_otp(clean_email, code, purpose)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    payload: Dict[str, Any] = {
        "otp_required": True,
        "challenge_id": str(challenge_id),
        "email": clean_email,
        "purpose": purpose,
        "expires_in_seconds": 600,
    }
    if is_dev_mode() or clean_email.endswith((".local", ".test", ".example")):
        payload["dev_otp_preview"] = code
    return payload


def _consume_otp(body: OtpVerificationRequest, purpose: str) -> Dict[str, Any]:
    email = body.email.strip().lower()
    factory = get_session_factory()
    failure: Optional[tuple[int, str]] = None
    user_id: Optional[str] = None
    now = datetime.now(timezone.utc)
    with factory() as session, session.begin():
        challenge = session.scalar(
            select(AuthOtpChallengeModel)
            .where(
                AuthOtpChallengeModel.id == body.challenge_id,
                AuthOtpChallengeModel.email == email,
                AuthOtpChallengeModel.purpose == purpose,
            )
            .with_for_update()
        )
        if challenge is None:
            failure = (400, "Verification code is invalid or expired.")
        elif challenge.consumed_at is not None:
            failure = (400, "Verification code is invalid or expired.")
        elif challenge.expires_at <= now:
            failure = (400, "Verification code is invalid or expired.")
        elif challenge.attempts >= challenge.max_attempts:
            failure = (429, "Too many verification attempts. Request a new code.")
        elif not hmac.compare_digest(
            challenge.code_hash,
            _otp_hash(challenge.id, email, purpose, body.otp_code),
        ):
            challenge.attempts += 1
            failure = (400, "Verification code is incorrect.")
        elif challenge.user_id is None:
            failure = (400, "Verification code is invalid or expired.")
        else:
            challenge.consumed_at = now
            user_id = str(challenge.user_id)
            user = session.get(UserModel, challenge.user_id)
            if user is None or user.email.strip().lower() != email:
                failure = (400, "Verification code is invalid or expired.")
                user_id = None
            elif purpose == "REGISTER_VERIFY":
                user.email_verified = True

    if failure:
        raise HTTPException(status_code=failure[0], detail=failure[1])
    user = PostgresUserRepository().get_by_id(user_id or "")
    if not user or (purpose == "LOGIN_2FA" and not user.get("email_verified", False)):
        raise HTTPException(status_code=400, detail="Verification code is invalid or expired.")
    return user


def _issue_session(response: Response, user: Dict[str, Any], action: str) -> LoginResponse:
    user_id = str(user["id"])
    email = str(user["email"])
    roles = list(user.get("roles") or [])
    access_token, access_jti = create_access_token(user_id=user_id, email=email, roles=roles)
    refresh_token, refresh_jti = create_refresh_token(user_id=user_id, email=email, roles=roles)
    _set_session_cookies(response, access_token, refresh_token)
    get_audit_service().record_event(
        actor=user_id,
        action=action,
        target=f"user:{user_id}",
        payload={"access_jti": access_jti, "refresh_jti": refresh_jti},
    )
    quota = user.get("quota_counters") or {}
    return LoginResponse(
        id=user_id,
        email=email,
        roles=roles,
        full_name=quota.get("full_name"),
        access_token=access_token,
    )


def _verify_google_id_token(raw_token: str) -> Dict[str, Any]:
    client_ids = get_google_client_ids()
    if not client_ids:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")

    try:
        if jwt.get_unverified_header(raw_token).get("alg") != "RS256":
            raise ValueError("Google ID token must use RS256.")
        signing_key = get_google_jwks_client().get_signing_key_from_jwt(raw_token)
        claims = jwt.decode(
            raw_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=list(client_ids),
            leeway=120,
            options={"require": ["aud", "exp", "iss", "sub", "email", "email_verified"]},
        )
    except Exception as jwks_error:
        # Google's HTTPS tokeninfo endpoint is a secondary verifier for key
        # fetch/rotation outages. It verifies the token before returning claims.
        try:
            query = urlencode({"id_token": raw_token})
            with urlopen(f"https://oauth2.googleapis.com/tokeninfo?{query}", timeout=5) as response:
                claims = json.loads(response.read().decode("utf-8"))
        except Exception as tokeninfo_error:
            raise HTTPException(
                status_code=401,
                detail="Google identity token is invalid or expired.",
            ) from jwks_error

    if claims.get("aud") not in client_ids or claims.get("iss") not in (
        "https://accounts.google.com",
        "accounts.google.com",
    ):
        raise HTTPException(status_code=401, detail="Google identity token is not valid for this application.")
    try:
        expiration = float(claims.get("exp"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Google identity token is invalid or expired.") from exc
    if expiration <= time.time() - 120:
        raise HTTPException(status_code=401, detail="Google identity token is invalid or expired.")
    email_verified = claims.get("email_verified")
    if (
        email_verified is not True
        and not (isinstance(email_verified, str) and email_verified.lower() == "true")
    ) or not claims.get("sub") or not claims.get("email"):
        raise HTTPException(status_code=401, detail="Google must provide a verified email address.")
    return claims


def _validate_registration(body: RegisterRequest) -> tuple[str, str, str]:
    email = body.email.strip().lower()
    full_name = body.full_name.strip()
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format.")
    if len(full_name) < 2:
        raise HTTPException(status_code=400, detail="Full name must contain at least two characters.")
    try:
        validate_password_strength(body.password)
    except PasswordValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return email, full_name, hash_password(body.password)


def _initiate_registration(body: RegisterRequest) -> Dict[str, Any]:
    email, full_name, password_hash = _validate_registration(body)
    repo = PostgresUserRepository()
    existing = repo.get_by_email(email)
    if existing and existing.get("email_verified", False):
        raise HTTPException(status_code=409, detail="An account with this email address already exists.")
    if existing:
        user_id = repo.update_unverified_user(email, password_hash, full_name)
        if not user_id:
            raise HTTPException(status_code=409, detail="An account with this email address already exists.")
    else:
        try:
            user_id = repo.create_user({
                "email": email,
                "password_hash": password_hash,
                "email_verified": False,
                "auth_provider": "local",
                "two_factor_enabled": True,
                "roles": [Role.ENTREPRENEUR.value],
                "quota_counters": {
                    "full_name": full_name,
                    "is_active": True,
                    "runs_today": 0,
                    "cost_today": 0.0,
                },
            })
        except UserAlreadyExistsError:
            existing = repo.get_by_email(email)
            if not existing or existing.get("email_verified", False):
                raise HTTPException(status_code=409, detail="An account with this email address already exists.")
            user_id = repo.update_unverified_user(email, password_hash, full_name)
            if not user_id:
                raise HTTPException(status_code=409, detail="An account with this email address already exists.")

    get_audit_service().record_event(
        actor=user_id,
        action="AUTH_REGISTER_OTP_INITIATED",
        target=f"user:{user_id}",
        payload={"purpose": "REGISTER_VERIFY"},
    )
    return _new_otp_challenge(user_id, email, "REGISTER_VERIFY")


def _legacy_register(request: Request, response: Response, body: RegisterRequest) -> LoginResponse:
    email, full_name, password_hash = _validate_registration(body)
    repo = PostgresUserRepository()
    try:
        user_id = repo.create_user({
            "email": email,
            "password_hash": password_hash,
            "email_verified": True,
            "auth_provider": "local",
            "two_factor_enabled": True,
            "roles": [Role.ENTREPRENEUR.value],
            "quota_counters": {"full_name": full_name, "is_active": True, "runs_today": 0, "cost_today": 0.0},
        })
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="An account with this email address already exists.") from exc
    user = repo.get_by_id(user_id) or {}
    return _issue_session(response, user, "AUTH_REGISTER")


def _authenticate_password(body: LoginRequest, request: Request) -> Dict[str, Any]:
    email = body.email.strip().lower()
    user = PostgresUserRepository().get_by_email(email)
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        get_audit_service().record_event(
            actor=None,
            action="AUTH_LOGIN_FAILURE",
            target=f"email:{email}",
            payload={"ip": request.client.host if request.client else "127.0.0.1", "reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if (user.get("quota_counters") or {}).get("is_active") is False:
        get_audit_service().record_event(
            actor=user["id"], action="AUTH_LOGIN_DEACTIVATED", target=f"user:{user['id']}", payload={},
        )
        raise HTTPException(status_code=403, detail="Account has been deactivated. Please contact an administrator.")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: Request, response: Response, body: RegisterRequest) -> Dict[str, Any]:
    """Legacy registration path for tests; production clients receive an OTP challenge."""
    if _legacy_auth_bypass(request):
        return _legacy_register(request, response, body).model_dump()
    response.status_code = status.HTTP_202_ACCEPTED
    return _initiate_registration(body)


@router.post("/register/initiate", status_code=status.HTTP_202_ACCEPTED)
def initiate_registration(body: RegisterRequest) -> Dict[str, Any]:
    return _initiate_registration(body)


@router.post("/register/verify-otp")
def verify_registration_otp(body: OtpVerificationRequest, response: Response) -> LoginResponse:
    user = _consume_otp(body, "REGISTER_VERIFY")
    return _issue_session(response, user, "AUTH_REGISTER_VERIFIED")


@router.post("/login")
def login(request: Request, response: Response, body: LoginRequest) -> Dict[str, Any]:
    """Legacy token-returning login is allowed only in tests or explicitly in development."""
    user = _authenticate_password(body, request)
    if _legacy_auth_bypass(request):
        return _issue_session(response, user, "AUTH_LOGIN_SUCCESS").model_dump()
    if not user.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before signing in.")
    response.status_code = status.HTTP_202_ACCEPTED
    return _new_otp_challenge(user["id"], user["email"], "LOGIN_2FA")


@router.post("/login/initiate", status_code=status.HTTP_202_ACCEPTED)
def initiate_login(request: Request, body: LoginRequest) -> Dict[str, Any]:
    user = _authenticate_password(body, request)
    if not user.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before signing in.")
    return _new_otp_challenge(user["id"], user["email"], "LOGIN_2FA")


@router.post("/login/verify-otp")
def verify_login_otp(body: OtpVerificationRequest, response: Response) -> LoginResponse:
    user = _consume_otp(body, "LOGIN_2FA")
    return _issue_session(response, user, "AUTH_LOGIN_SUCCESS")


@router.post("/otp/resend", status_code=status.HTTP_202_ACCEPTED)
def resend_otp(body: OtpResendRequest) -> Dict[str, Any]:
    email = body.email.strip().lower()
    factory = get_session_factory()
    with factory() as session:
        challenge = session.scalar(select(AuthOtpChallengeModel).where(
            AuthOtpChallengeModel.id == body.challenge_id,
            AuthOtpChallengeModel.email == email,
        ))
        if challenge is None or challenge.consumed_at is not None:
            raise HTTPException(status_code=400, detail="Verification challenge is unavailable. Start again.")
        purpose = challenge.purpose
        user_id = str(challenge.user_id) if challenge.user_id else None
    if purpose not in {"REGISTER_VERIFY", "LOGIN_2FA"} or not user_id:
        raise HTTPException(status_code=400, detail="Verification challenge is unavailable. Start again.")
    user = PostgresUserRepository().get_by_id(user_id)
    if not user or user["email"].lower() != email:
        raise HTTPException(status_code=400, detail="Verification challenge is unavailable. Start again.")
    if purpose == "REGISTER_VERIFY" and user.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Email is already verified.")
    if purpose == "LOGIN_2FA" and not user.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before signing in.")
    return _new_otp_challenge(user_id, email, purpose)


@router.post("/google")
def google_auth(body: GoogleAuthRequest, request: Request, response: Response) -> LoginResponse:
    client_ids = get_google_client_ids()
    production = is_production_environment()
    if body.id_token and (client_ids or production):
        claims = _verify_google_id_token(body.id_token)
        email = str(claims["email"]).strip().lower()
        name = str(claims.get("name") or body.full_name or email.split("@", 1)[0]).strip()
        google_sub = str(claims["sub"])
        provider = "google"
    elif not production and is_dev_mode() and body.email and body.full_name:
        email = body.email.strip().lower()
        if not EMAIL_REGEX.match(email):
            raise HTTPException(status_code=400, detail="Invalid email format.")
        name = body.full_name.strip()
        google_sub = "dev-google:" + hashlib.sha256(email.encode("utf-8")).hexdigest()
        provider = "google-dev"
    else:
        raise HTTPException(status_code=401, detail="A verified Google identity token is required.")

    repo = PostgresUserRepository()
    user = repo.get_by_google_sub(google_sub)
    if user is None:
        existing = repo.get_by_email(email)
        if existing:
            if not existing.get("email_verified", False):
                raise HTTPException(status_code=403, detail="Verify this email address before linking Google sign-in.")
            if existing.get("google_sub") and existing["google_sub"] != google_sub:
                raise HTTPException(status_code=409, detail="This email is linked to a different Google account.")
            if not repo.link_google_identity(existing["id"], google_sub):
                raise HTTPException(status_code=404, detail="Account is unavailable.")
            user = repo.get_by_id(existing["id"])
        else:
            try:
                user_id = repo.create_user({
                    "email": email,
                    "password_hash": hash_password(secrets.token_urlsafe(48)),
                    "email_verified": True,
                    "google_sub": google_sub,
                    "auth_provider": provider,
                    "two_factor_enabled": True,
                    "roles": [Role.ENTREPRENEUR.value],
                    "quota_counters": {"full_name": name, "is_active": True, "runs_today": 0, "cost_today": 0.0},
                })
                user = repo.get_by_id(user_id)
            except UserAlreadyExistsError as exc:
                user = repo.get_by_google_sub(google_sub)
                if user is None:
                    raise HTTPException(status_code=409, detail="An account with this email address already exists.") from exc

    if not user or not user.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google account could not be verified.")
    get_audit_service().record_event(
        actor=user["id"], action="AUTH_GOOGLE_SUCCESS", target=f"user:{user['id']}",
        payload={"provider": user.get("auth_provider", provider), "mode": body.mode},
    )
    return _issue_session(response, user, "AUTH_GOOGLE_SESSION")


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

        if is_test_environment() or is_dev_mode() or clean_email.endswith((".local", ".test", ".example")):
            dev_token = reset_token
            dev_url = f"/reset-password?token={reset_token}"

    response_payload: Dict[str, Any] = {
        "status": "ok",
        "message": "If an account exists with this email, password recovery instructions have been sent.",
    }
    if dev_token:
        response_payload["dev_recovery_token"] = dev_token
        response_payload["dev_reset_url"] = dev_url

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


@router.post("/refresh", response_model=LoginResponse)
def refresh_session(request: Request, response: Response) -> LoginResponse:
    """Rotate the refresh cookie and issue a fresh short-lived access token."""
    cookie_name = get_auth_cookie_name()
    refresh_cookie_name = f"{cookie_name}{REFRESH_COOKIE_SUFFIX}"
    refresh_token = request.cookies.get(refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is missing.")
    try:
        claims = decode_access_token(refresh_token)
    except (TokenExpiredError, TokenInvalidError, TokenRevokedError) as exc:
        response.delete_cookie(refresh_cookie_name, path="/auth")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is invalid or expired.") from exc
    if claims.get("token_type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access credentials cannot refresh a session.")

    repo = PostgresUserRepository()
    user = repo.get_by_id(claims.get("sub", ""))
    quota = (user or {}).get("quota_counters") or {}
    if not user or quota.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is unavailable.")

    revocation = get_token_revocation_store()
    revocation.revoke(
        claims["jti"],
        datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
    )
    roles = user.get("roles") or []
    access_token, access_jti = create_access_token(
        user_id=user["id"], email=user["email"], roles=roles,
    )
    next_refresh, refresh_jti = create_refresh_token(
        user_id=user["id"], email=user["email"], roles=roles,
    )
    _set_session_cookies(response, access_token, next_refresh)
    get_audit_service().record_event(
        actor=user["id"],
        action="AUTH_SESSION_REFRESHED",
        target=f"user:{user['id']}",
        payload={"prior_refresh_jti": claims["jti"], "access_jti": access_jti, "refresh_jti": refresh_jti},
    )
    return LoginResponse(
        id=user["id"], email=user["email"], roles=roles,
        full_name=quota.get("full_name"), access_token=access_token,
    )


@router.post("/logout")
def logout(request: Request, response: Response) -> Dict[str, str]:
    """
    Invalidate session: revoke token JTI in revocation store and delete session cookie.
    """
    cookie_name = get_auth_cookie_name()
    token = request.cookies.get(cookie_name)
    refresh_token = request.cookies.get(f"{cookie_name}{REFRESH_COOKIE_SUFFIX}")
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
    if refresh_token:
        try:
            claims = decode_access_token(refresh_token)
            revocation.revoke(
                claims["jti"],
                datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
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
    response.delete_cookie(
        key=f"{cookie_name}{REFRESH_COOKIE_SUFFIX}",
        httponly=True,
        secure=get_auth_cookie_secure(),
        samesite=get_auth_cookie_samesite(),
        path="/auth",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        httponly=False,
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
