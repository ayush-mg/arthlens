"""
Integration Tests for Authentication Endpoints (POST /auth/login and POST /auth/logout).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies:
- Successful login sets HTTP-only cookie and returns user profile.
- Invalid password returns generic 401 without account enumeration.
- Unknown email returns generic 401 without account enumeration.
- Logout clears the session cookie and revokes token.
- Subsequent calls using the logged-out token fail with 401 Unauthorized.
- Cookie attributes (HttpOnly, SameSite) are correctly set.
"""

from io import BytesIO
import json
import time
import uuid

import jwt
import jwt.jwks_client
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra import config as app_config
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role


def _csrf_headers(client):
    token = client.cookies.get("arthlens_csrf")
    return {"X-CSRF-Token": token} if token else {}


@pytest.fixture
def client(monkeypatch):
    # Legacy integration flows use the explicit development-only preview opt-in.
    # The application never exposes a code to the browser by default.
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("EXPOSE_DEV_OTP_ON_SCREEN", "true")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    app = create_app()
    return TestClient(app)


@pytest.fixture
def seeded_user():
    """Create a verified test user in PostgreSQL."""
    repo = PostgresUserRepository()
    email = f"test_{uuid.uuid4().hex[:8]}@arthlens.org"
    password = "CorrectHorseBattery2026!"
    password_hash = hash_password(password)

    user_id = repo.save({
        "email": email,
        "password_hash": password_hash,
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    return {"id": user_id, "email": email, "password": password}


@pytest.fixture
def google_signing_setup(monkeypatch):
    """Issue real RS256 ID tokens while serving a test JWKS through PyJWKClient."""
    client_id = "arthlens-google-client.apps.googleusercontent.com"
    key_id = "arthlens-integration-google-key"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", client_id)
    app_config.get_google_jwks_client.cache_clear()

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": key_id, "use": "sig", "alg": "RS256"})
    jwks_payload = json.dumps({"keys": [jwk]}).encode("utf-8")
    fetches = []

    class JwksOpener:
        def open(self, request, timeout):
            fetches.append((request.full_url, timeout))
            return BytesIO(jwks_payload)

    monkeypatch.setattr(
        jwt.jwks_client.urllib.request,
        "build_opener",
        lambda *_handlers: JwksOpener(),
    )

    def issue_token(audience=client_id, email_verified=True, expires_in=300):
        now = int(time.time())
        return jwt.encode(
            {
                "iss": "https://accounts.google.com",
                "aud": audience,
                "exp": now + expires_in,
                "iat": now,
                "sub": "google-user-arthlens-integration",
                "email": "verified.google.user@example.com",
                "email_verified": email_verified,
                "name": "Verified Google User",
            },
            private_key,
            algorithm="RS256",
            headers={"kid": key_id},
        )

    yield client_id, issue_token, fetches
    app_config.get_google_jwks_client.cache_clear()


@pytest.mark.integration
class TestAuthEndpoints:
    """Tests /auth/login and /auth/logout workflows."""

    def test_login_success_sets_cookie_and_returns_user(self, client, seeded_user):
        """Successful login returns user info and sets HttpOnly session cookie."""
        res = client.post("/auth/login", json={
            "email": seeded_user["email"],
            "password": seeded_user["password"],
        })
        assert res.status_code == 200
        body = res.json()
        assert body["email"] == seeded_user["email"]
        assert "ENTREPRENEUR" in body["roles"]

        # Verify cookie
        cookie_name = get_auth_cookie_name()
        assert cookie_name in res.cookies
        cookie_header = res.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()

    def test_password_login_requires_and_consumes_email_otp(self, client, seeded_user):
        initiated = client.post("/auth/login/initiate", json={
            "email": seeded_user["email"], "password": seeded_user["password"],
        })
        assert initiated.status_code == 202
        challenge = initiated.json()
        assert challenge["otp_required"] is True
        assert challenge["purpose"] == "LOGIN_2FA"
        assert "access_token" not in challenge
        assert len(challenge["dev_otp_preview"]) == 6

        verified = client.post("/auth/login/verify-otp", json={
            "challenge_id": challenge["challenge_id"],
            "email": seeded_user["email"],
            "otp_code": challenge["dev_otp_preview"],
        })
        assert verified.status_code == 200
        assert verified.json()["email"] == seeded_user["email"]
        assert get_auth_cookie_name() in verified.cookies

        replay = client.post("/auth/login/verify-otp", json={
            "challenge_id": challenge["challenge_id"],
            "email": seeded_user["email"],
            "otp_code": challenge["dev_otp_preview"],
        }, headers=_csrf_headers(client))
        assert replay.status_code == 400

    def test_otp_preview_is_never_returned_for_smtp_delivery(self, client, seeded_user, monkeypatch):
        from backend.arthlens.api import auth

        monkeypatch.setattr(auth, "send_email_otp", lambda *_args: (True, "smtp"))
        response = client.post("/auth/login/initiate", json={
            "email": seeded_user["email"], "password": seeded_user["password"],
        })

        assert response.status_code == 202
        assert "dev_otp_preview" not in response.json()

    def test_otp_preview_requires_explicit_development_opt_in(self, client, seeded_user, monkeypatch):
        from backend.arthlens.api import auth

        monkeypatch.delenv("EXPOSE_DEV_OTP_ON_SCREEN")
        monkeypatch.setattr(auth, "send_email_otp", lambda *_args: (True, "development-console"))
        response = client.post("/auth/login/initiate", json={
            "email": seeded_user["email"], "password": seeded_user["password"],
        })

        assert response.status_code == 202
        assert "dev_otp_preview" not in response.json()

    def test_otp_attempts_are_limited_and_resend_invalidates_prior_code(self, client, seeded_user):
        initiated = client.post("/auth/login/initiate", json={
            "email": seeded_user["email"], "password": seeded_user["password"],
        })
        challenge = initiated.json()
        for _ in range(5):
            response = client.post("/auth/login/verify-otp", json={
                "challenge_id": challenge["challenge_id"], "email": seeded_user["email"], "otp_code": "000000",
            })
            assert response.status_code == 400

        locked = client.post("/auth/login/verify-otp", json={
            "challenge_id": challenge["challenge_id"], "email": seeded_user["email"], "otp_code": challenge["dev_otp_preview"],
        })
        assert locked.status_code == 429

        replacement = client.post("/auth/otp/resend", json={
            "challenge_id": challenge["challenge_id"], "email": seeded_user["email"],
        })
        assert replacement.status_code == 202
        next_challenge = replacement.json()
        stale = client.post("/auth/login/verify-otp", json={
            "challenge_id": challenge["challenge_id"], "email": seeded_user["email"],
            "otp_code": challenge["dev_otp_preview"],
        })
        assert stale.status_code == 400
        success = client.post("/auth/login/verify-otp", json={
            "challenge_id": next_challenge["challenge_id"], "email": seeded_user["email"],
            "otp_code": next_challenge["dev_otp_preview"],
        })
        assert success.status_code == 200

    def test_login_invalid_password_returns_generic_401(self, client, seeded_user):
        """Invalid password returns generic 401 without revealing password was wrong."""
        res = client.post("/auth/login", json={
            "email": seeded_user["email"],
            "password": "WrongPassword123!",
        })
        assert res.status_code == 401
        assert "invalid" in res.json()["detail"].lower()

    def test_login_unknown_email_returns_identical_generic_401(self, client):
        """Unknown email returns identical generic 401 error message to prevent enumeration."""
        res = client.post("/auth/login", json={
            "email": "nonexistent_user_99999@arthlens.org",
            "password": "SomePassword123!",
        })
        assert res.status_code == 401
        assert "invalid" in res.json()["detail"].lower()

    def test_logout_clears_cookie_and_revokes_token(self, client, seeded_user):
        """Logging out clears cookie and revokes token so it cannot be reused."""
        cookie_name = get_auth_cookie_name()

        # 1. Login
        login_res = client.post("/auth/login", json={
            "email": seeded_user["email"],
            "password": seeded_user["password"],
        })
        token = login_res.cookies[cookie_name]

        # 2. Access protected endpoint -> succeeds
        res_auth = client.get("/auth/me", cookies={cookie_name: token})
        assert res_auth.status_code == 200
        assert res_auth.json()["email"] == seeded_user["email"]

        # 3. Logout
        logout_res = client.post(
            "/auth/logout",
            cookies={cookie_name: token},
            headers=_csrf_headers(client),
        )
        assert logout_res.status_code == 200

        # Verify response cleared cookie (Max-Age=0 or expired)
        set_cookie = logout_res.headers.get("set-cookie", "")
        assert cookie_name in set_cookie
        assert "max-age=0" in set_cookie.lower() or "expires=" in set_cookie.lower()

        # 4. Attempt to reuse previous token -> rejected (401 Token revoked)
        res_reused = client.get("/auth/me", cookies={cookie_name: token})
        assert res_reused.status_code == 401
        assert "revoked" in res_reused.json()["detail"].lower()

    def test_google_auth_verifies_rs256_jwks_token_and_caches_google_keys(
        self, client, google_signing_setup,
    ):
        client_id, issue_token, fetches = google_signing_setup
        token = issue_token()
        request = {"mode": "register", "id_token": token}

        registered = client.post("/auth/google", json=request)
        assert registered.status_code == 200, registered.text
        assert registered.json()["email"] == "verified.google.user@example.com"
        assert "ENTREPRENEUR" in registered.json()["roles"]

        signed_in = client.post(
            "/auth/google",
            json={**request, "mode": "login"},
            headers=_csrf_headers(client),
        )
        assert signed_in.status_code == 200, signed_in.text
        assert signed_in.json()["email"] == "verified.google.user@example.com"
        assert len(fetches) == 1
        assert fetches[0][0] == "https://www.googleapis.com/oauth2/v3/certs"
        assert fetches[0][1] <= 5
        assert jwt.decode(token, options={"verify_signature": False})["aud"] == client_id

    def test_google_auth_rejects_rs256_token_with_invalid_audience(
        self, client, google_signing_setup,
    ):
        _client_id, issue_token, _fetches = google_signing_setup
        response = client.post("/auth/google", json={
            "mode": "login",
            "id_token": issue_token(audience="another-application.apps.googleusercontent.com"),
        })
        assert response.status_code == 401
        assert "token" in response.json()["detail"].lower()

    def test_google_auth_accepts_frontend_audience_string_verification_and_clock_skew(
        self, client, google_signing_setup, monkeypatch,
    ):
        client_id, issue_token, _fetches = google_signing_setup
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", client_id)
        response = client.post("/auth/google", json={
            "mode": "register",
            "id_token": issue_token(email_verified="true", expires_in=-60),
        })
        assert response.status_code == 200, response.text
        assert response.json()["email"] == "verified.google.user@example.com"

    def test_google_auth_blocks_local_chooser_in_production(self, client, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", raising=False)
        response = client.post("/auth/google", json={
            "mode": "register",
            "email": "local.chooser@example.com",
            "full_name": "Local Chooser",
        })
        assert response.status_code == 401
        assert "verified google identity token" in response.json()["detail"].lower()
