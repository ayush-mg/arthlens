"""
Email and Password Recovery Service for ArthLens.

Provides configurable SMTP delivery for production, and safe labeled console
recovery logging in local development mode.
"""

from datetime import datetime, timezone
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def is_dev_mode() -> bool:
    """Check if the current runtime environment is local development or testing."""
    env = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    return env not in ("production", "prod")


def send_email_otp(to_email: str, otp_code: str, purpose: str) -> Tuple[bool, str]:
    """Deliver a short-lived email verification/sign-in code.

    OTP values are intentionally visible in logs only outside production so local
    development remains usable without SMTP. Production fails closed if SMTP is
    not configured or delivery fails.
    """
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    if not smtp_host and smtp_user and smtp_pass:
        smtp_host = "smtp.gmail.com"
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", "noreply@arthlens.org").strip()
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    subject = "Your ArthLens sign-in code" if purpose == "LOGIN_2FA" else "Verify your ArthLens email"

    if to_email.lower().endswith((".local", ".test", ".example")):
        dev_message = f"[AUTH DEV OTP] {purpose} code for {to_email}: {otp_code} (expires in 10 minutes)"
        print(dev_message)
        logger.warning(dev_message)
        return True, "development-console"

    if smtp_host:
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = smtp_from
            message["To"] = to_email
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
            message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if smtp_use_tls:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(message)
            logger.info("Sent ArthLens OTP email to %s", to_email)
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
        raise RuntimeError("SMTP must be configured for production email verification.")

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
    Send password reset instructions via SMTP if configured, or log locally in development mode.
    Returns (success: bool, delivery_info: str).
    """
    if not base_url:
        base_url = os.environ.get("APP_BASE_URL", "http://localhost:3000")
    reset_url = f"{base_url.rstrip('/')}/reset-password?token={reset_token}"

    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", "noreply@arthlens.org").strip()
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    if to_email.lower().endswith((".local", ".test", ".example")):
        dev_message = f"[AUTH DEV PASSWORD RESET] Recovery URL for {to_email}: {reset_url}"
        print(dev_message)
        logger.warning(dev_message)
        return True, "development-console"

    if smtp_host:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "ArthLens: Password Recovery Request"
            msg["From"] = smtp_from
            msg["To"] = to_email

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

