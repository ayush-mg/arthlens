"""
Email and Password Recovery Service for ArthLens.

Provides configurable SMTP delivery for production, and safe labeled console
recovery logging in local development mode.
"""

from datetime import datetime, timezone
import json
import logging
import os
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def is_dev_mode() -> bool:
    """Check if the current runtime environment is local development or testing."""
    env = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    return env not in ("production", "prod")


def _send_via_brevo(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str,
) -> Tuple[bool, str]:
    """Send an email via Brevo (Sendinblue) HTTPS REST API v3 (Port 443).

    Allows sending to ANY recipient in the world without requiring a custom domain;
    only sender email verification (via confirmation email) is needed.
    """
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    if not api_key:
        return False, "BREVO_API_KEY is not configured"

    sender_email = (
        os.environ.get("BREVO_SENDER_EMAIL")
        or os.environ.get("SMTP_FROM_EMAIL")
        or os.environ.get("SMTP_USER")
        or "noreply@arthlens.org"
    ).strip()
    sender_name = os.environ.get("BREVO_SENDER_NAME", "ArthLens Security").strip()

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content,
    }

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ArthLens-Backend/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            logger.info("Sent email to %s via Brevo HTTPS API: %s", to_email, resp_body)
            return True, "brevo"
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8")
        logger.error("Brevo API HTTP error %d: %s", exc.code, err_msg)
        raise RuntimeError(f"Brevo email delivery failed ({exc.code}): {err_msg}") from exc
    except Exception as exc:
        logger.error("Brevo API connection error: %s", exc)
        raise RuntimeError(f"Brevo email delivery connection failed: {exc}") from exc


def _send_via_resend(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str,
) -> Tuple[bool, str]:
    """Send an email via Resend's HTTPS REST API (Port 443).

    Operates over standard outbound HTTPS (Port 443), bypassing outbound SMTP
    port blocks (25, 465, 587) enforced by cloud providers such as Render Free.
    """
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        return False, "RESEND_API_KEY is not configured"

    from_email = os.environ.get("RESEND_FROM_EMAIL", "").strip()
    if not from_email:
        candidate = os.environ.get("SMTP_FROM_EMAIL", "").strip()
        if candidate and not any(
            candidate.lower().endswith(d)
            for d in ("@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com", "@icloud.com")
        ):
            from_email = candidate
        else:
            from_email = "ArthLens <onboarding@resend.dev>"

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "text": text_content,
    }

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ArthLens-Backend/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            logger.info("Sent email to %s via Resend HTTPS API: %s", to_email, resp_body)
            return True, "resend"
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8")
        logger.error("Resend API HTTP error %d: %s", exc.code, err_msg)
        raise RuntimeError(f"Resend email delivery failed ({exc.code}): {err_msg}") from exc
    except Exception as exc:
        logger.error("Resend API connection error: %s", exc)
        raise RuntimeError(f"Resend email delivery connection failed: {exc}") from exc


def send_email_otp(to_email: str, otp_code: str, purpose: str) -> Tuple[bool, str]:
    """Deliver a short-lived email verification/sign-in code.

    Supports:
    1. Local/sandbox test domains (.local, .test, .example) -> instant development console/preview
    2. Resend HTTPS REST API (RESEND_API_KEY) -> outbound port 443 (recommended for cloud hosts)
    3. SMTP delivery (SMTP_HOST / SMTP_USER / SMTP_PASSWORD) -> outbound port 587
    4. Safe development fallback when running outside production
    """
    subject = "Your ArthLens sign-in code" if purpose == "LOGIN_2FA" else "Verify your ArthLens email"
    text_body = (
        f"Your ArthLens verification code is {otp_code}.\n\n"
        "It expires in 10 minutes and can be used once. If you did not request it, ignore this email."
    )
    html_body = (
        '<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:28px;'
        'background:#0b0f17;color:#f8fafc;border:1px solid #263244;border-radius:20px">'
        '<p style="color:#34d399;font-size:12px;letter-spacing:.18em;text-transform:uppercase">ArthLens security</p>'
        f'<h1 style="font-size:28px">{subject}</h1>'
        f'<p style="font-size:34px;letter-spacing:.32em;font-weight:700">{otp_code}</p>'
        '<p style="color:#94a3b8">This code expires in 10 minutes and can be used once.</p></div>'
    )

    if to_email.lower().endswith((".local", ".test", ".example")):
        dev_message = f"[AUTH DEV OTP] {purpose} code for {to_email}: {otp_code} (expires in 10 minutes)"
        print(dev_message)
        logger.warning(dev_message)
        return True, "development-console"

    # 1. Brevo (Sendinblue) HTTPS REST API v3 (Sends to any recipient without requiring a custom domain)
    if os.environ.get("BREVO_API_KEY", "").strip():
        try:
            return _send_via_brevo(to_email, subject, text_body, html_body)
        except Exception as exc:
            logger.exception("Failed to deliver ArthLens OTP via Brevo to %s", to_email)
            if is_dev_mode():
                logger.warning("Brevo failed in dev mode; falling back to console OTP: %s", exc)
                dev_message = f"[AUTH DEV OTP] {purpose} code for {to_email}: {otp_code} (expires in 10 minutes)"
                print(dev_message)
                return True, "development-console"
            raise RuntimeError(f"Email verification delivery failed: {exc}") from exc

    # 2. Resend HTTPS REST API (bypasses outbound SMTP port blocks)
    if os.environ.get("RESEND_API_KEY", "").strip():
        try:
            return _send_via_resend(to_email, subject, text_body, html_body)
        except Exception as exc:
            logger.exception("Failed to deliver ArthLens OTP via Resend to %s", to_email)
            if is_dev_mode():
                logger.warning("Resend failed in dev mode; falling back to console OTP: %s", exc)
                dev_message = f"[AUTH DEV OTP] {purpose} code for {to_email}: {otp_code} (expires in 10 minutes)"
                print(dev_message)
                return True, "development-console"
            raise RuntimeError(f"Email verification delivery failed: {exc}") from exc

    # 2. SMTP Delivery (port 587)
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    if not smtp_host and smtp_user and smtp_pass:
        smtp_host = "smtp.gmail.com"
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", "noreply@arthlens.org").strip()
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    if smtp_host:
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = smtp_from
            message["To"] = to_email
            message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if smtp_use_tls:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(message)
            logger.info("Sent ArthLens OTP email to %s via SMTP %s", to_email, smtp_host)
            return True, "smtp"
        except Exception as exc:
            logger.exception("Failed to send ArthLens OTP email to %s", to_email)
            if is_dev_mode():
                logger.warning("SMTP failed in dev mode; falling back to console OTP: %s", exc)
                dev_message = f"[AUTH DEV OTP] {purpose} code for {to_email}: {otp_code} (expires in 10 minutes)"
                print(dev_message)
                return True, "development-console"
            raise RuntimeError("Email verification delivery is unavailable.") from exc

    if not is_dev_mode():
        raise RuntimeError("Email delivery is unavailable. Configure RESEND_API_KEY or SMTP credentials.")

    dev_message = f"[AUTH DEV OTP] {purpose} code for {to_email}: {otp_code} (expires in 10 minutes)"
    print(dev_message)
    logger.warning(dev_message)

    return True, "development-console"


def send_password_reset_email(
    to_email: str,
    reset_token: str,
    base_url: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Send password reset instructions via Resend HTTPS API or SMTP if configured,
    or log locally in development mode.
    Returns (success: bool, delivery_info: str).
    """
    if not base_url:
        candidate_base = os.environ.get("APP_BASE_URL") or os.environ.get("FRONTEND_URL")
        if not candidate_base:
            allowed = os.environ.get("ALLOWED_ORIGINS", "")
            for orig in [o.strip() for o in allowed.split(",") if o.strip()]:
                if not any(lh in orig.lower() for lh in ("localhost", "127.0.0.1")):
                    candidate_base = orig
                    break
        if not candidate_base:
            candidate_base = "https://arthlens-two.vercel.app" if not is_dev_mode() else "http://localhost:3000"
        base_url = candidate_base
    reset_url = f"{base_url.rstrip('/')}/reset-password?token={reset_token}"
    subject = "ArthLens: Password Recovery Request"
    text_content = (
        f"You requested a password reset for your ArthLens account.\n\n"
        f"Reset Link: {reset_url}\n\n"
        f"This single-use link will expire in 15 minutes.\n"
        f"If you did not request this, please disregard this email."
    )
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #2D4A3E;">ArthLens Password Recovery</h2>
      <p>You requested a password reset for your ArthLens account.</p>
      <p style="margin: 24px 0;">
        <a href="{reset_url}" style="background-color: #C17C54; color: #FFF; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">
          Reset Password
        </a>
      </p>
      <p style="color: #666; font-size: 12px;">This single-use link expires in 15 minutes. If you did not request this, no action is needed.</p>
    </div>
    """

    if to_email.lower().endswith((".local", ".test", ".example")):
        dev_message = f"[AUTH DEV PASSWORD RESET] Recovery URL for {to_email}: {reset_url}"
        print(dev_message)
        logger.warning(dev_message)
        return True, "development-console"

    # 1. Brevo (Sendinblue) HTTPS REST API v3
    if os.environ.get("BREVO_API_KEY", "").strip():
        try:
            return _send_via_brevo(to_email, subject, text_content, html_content)
        except Exception as exc:
            logger.error("Failed to send password reset via Brevo to %s: %s", to_email, exc)
            if is_dev_mode():
                dev_msg = f"[AUTH DEV RECOVERY] Password recovery token for {to_email}: {reset_token} (URL: {reset_url})"
                print(dev_msg)
                return True, f"Logged to local development console: {reset_url}"
            raise

    # 2. Resend HTTPS REST API
    if os.environ.get("RESEND_API_KEY", "").strip():
        try:
            return _send_via_resend(to_email, subject, text_content, html_content)
        except Exception as exc:
            logger.error("Failed to send password reset via Resend to %s: %s", to_email, exc)
            if is_dev_mode():
                dev_msg = f"[AUTH DEV RECOVERY] Password recovery token for {to_email}: {reset_token} (URL: {reset_url})"
                print(dev_msg)
                return True, f"Logged to local development console: {reset_url}"
            raise

    # 2. SMTP Delivery
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", "noreply@arthlens.org").strip()
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    if smtp_host:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = to_email
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if smtp_use_tls:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info("Sent password recovery email to %s via SMTP %s", to_email, smtp_host)
            return True, f"Sent via SMTP {smtp_host}"
        except Exception as exc:
            logger.error("Failed to send SMTP password reset to %s: %s", to_email, exc)

    # Local development fallback mechanism
    dev_msg = f"[AUTH DEV RECOVERY] Password recovery token for {to_email}: {reset_token} (URL: {reset_url})"
    print(dev_msg)
    logger.info(dev_msg)
    return True, f"Logged to local development console: {reset_url}"

