"""Exercise the live ArthLens stack with a disposable, archived workspace."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


class SmokeCheckError(RuntimeError):
    pass


def request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    accept: str = "application/json, application/pdf",
) -> tuple[int, bytes, dict[str, str]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": accept}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise SmokeCheckError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SmokeCheckError(f"{method} {path} could not reach the service: {exc}") from exc


def expect_status(result: tuple[int, bytes, dict[str, str]], expected: int, label: str) -> bytes:
    status, body, _ = result
    if status != expected:
        raise SmokeCheckError(f"{label}: expected HTTP {expected}, got {status}")
    return body


def login_with_email_otp(base_url: str, email: str, password: str, otp_code: str | None) -> dict[str, Any]:
    challenge = json.loads(expect_status(
        request(
            base_url,
            "/auth/login/initiate",
            method="POST",
            payload={"email": email, "password": password},
        ),
        202,
        "email/password login initiation",
    ))
    code = challenge.get("dev_otp_preview") or otp_code or os.getenv("ARTHLENS_SMOKE_OTP")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise SmokeCheckError(
            "login requires a dev_otp_preview or a six digit --otp-code/ARTHLENS_SMOKE_OTP value"
        )
    auth = json.loads(expect_status(
        request(
            base_url,
            "/auth/login/verify-otp",
            method="POST",
            payload={
                "challenge_id": challenge.get("challenge_id"),
                "email": challenge.get("email") or email,
                "otp_code": code,
            },
        ),
        200,
        "email OTP verification",
    ))
    if not auth.get("access_token"):
        raise SmokeCheckError("OTP verification response did not contain an access token")
    return auth


def check_google_auth_flows(base_url: str, suffix: str, google_id_token: str | None) -> None:
    configured_client = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    environment = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if not google_id_token and (configured_client or environment in {"production", "prod"}):
        raise SmokeCheckError(
            "configured Google authentication requires --google-id-token/ARTHLENS_SMOKE_GOOGLE_ID_TOKEN"
        )

    email = f"arthlens-smoke-google-{suffix}@arthlens.local"
    payload: dict[str, Any]
    if google_id_token:
        payload = {"id_token": google_id_token}
    else:
        payload = {"email": email, "full_name": "ArthLens Google Smoke"}

    for mode in ("register", "login"):
        auth = json.loads(expect_status(
            request(
                base_url,
                "/auth/google",
                method="POST",
                payload={"mode": mode, **payload},
            ),
            200,
            f"Google sign-in {mode} flow",
        ))
        if not auth.get("access_token"):
            raise SmokeCheckError(f"Google sign-in {mode} response did not contain an access token")
        email = auth.get("email") or email
        print(f"PASS Google sign-in {mode} flow")


def check_auth_pages(web_base_url: str) -> None:
    for path, heading in (("/login", "Welcome back"), ("/register", "Create your account")):
        status, body, headers = request(web_base_url, path, accept="text/html")
        content_type = next((value for key, value in headers.items() if key.lower() == "content-type"), "")
        html = body.decode("utf-8", errors="replace")
        if status != 200 or "text/html" not in content_type.lower():
            raise SmokeCheckError(f"frontend {path} did not return an HTML page")
        if heading not in html or "Google" not in html:
            raise SmokeCheckError(f"frontend {path} is missing its auth screen or Google Sign-In control")
        print(f"PASS frontend {path} Email OTP/Google auth screen")


def run(
    base_url: str,
    email: str,
    password: str,
    otp_code: str | None = None,
    google_id_token: str | None = None,
    web_base_url: str | None = None,
) -> None:
    for path, expected_value in (("/health/live", "live"), ("/health/ready", "ready")):
        raw = expect_status(request(base_url, path), 200, path)
        if json.loads(raw).get("status") != expected_value:
            raise SmokeCheckError(f"{path}: unexpected health response")
        print(f"PASS {path}")

    auth = login_with_email_otp(base_url, email, password, otp_code)
    token = auth["access_token"]
    print("PASS two-step email OTP login")

    suffix = f"{int(time.time())}-{os.getpid()}"
    check_google_auth_flows(base_url, suffix, google_id_token)
    if web_base_url:
        check_auth_pages(web_base_url)
    business_id: str | None = None
    try:
        workspace = json.loads(expect_status(request(
            base_url,
            "/businesses",
            method="POST",
            token=token,
            payload={"name": f"ArthLens smoke {suffix}", "industry": "Smoke verification"},
        ), 201, "workspace creation"))
        business_id = workspace.get("id")
        if not business_id:
            raise SmokeCheckError("workspace creation response omitted its id")
        print("PASS workspace creation")

        pnl = json.loads(expect_status(request(
            base_url,
            f"/businesses/{business_id}/analytics/pnl",
            token=token,
        ), 200, "financial snapshot"))
        if not isinstance(pnl, dict) or "provenance" not in pnl:
            raise SmokeCheckError("financial snapshot omitted its provenance block")
        print("PASS financial snapshot retrieval")

        status, pdf, headers = request(
            base_url,
            f"/businesses/{business_id}/reports/dossier.pdf",
            token=token,
        )
        content_type = next(
            (value for key, value in headers.items() if key.lower() == "content-type"),
            "",
        )
        if status != 200 or not pdf.startswith(b"%PDF-") or "pdf" not in content_type.lower():
            raise SmokeCheckError("report export did not return a PDF document")
        print("PASS authenticated report export")
    finally:
        if business_id:
            expect_status(request(
                base_url,
                f"/businesses/{business_id}/archive",
                method="POST",
                token=token,
                payload={"is_archived": True},
            ), 200, "smoke workspace cleanup")
            print("PASS smoke workspace archived")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ARTHLENS_SMOKE_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--email", default=os.getenv("ARTHLENS_SMOKE_EMAIL"))
    parser.add_argument("--password", default=os.getenv("ARTHLENS_SMOKE_PASSWORD"))
    parser.add_argument("--otp-code", default=os.getenv("ARTHLENS_SMOKE_OTP"))
    parser.add_argument("--google-id-token", default=os.getenv("ARTHLENS_SMOKE_GOOGLE_ID_TOKEN"))
    parser.add_argument("--web-base-url", default=os.getenv("ARTHLENS_SMOKE_WEB_BASE_URL"))
    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error("supply --email and --password or ARTHLENS_SMOKE_EMAIL/ARTHLENS_SMOKE_PASSWORD")
    try:
        run(
            args.base_url,
            args.email,
            args.password,
            otp_code=args.otp_code,
            google_id_token=args.google_id_token,
            web_base_url=args.web_base_url,
        )
    except SmokeCheckError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
