"""
One-time secure administrator bootstrap command.

Authoritative Specification: ArthLens Build Handbook Part 11, Part 13.1 P1-6.
Requirements:
- Read initial admin email and password from env vars or CLI arguments.
- Validate password strength and hash using Argon2id.
- Prevent repeated administrator bootstrap once an active admin exists.
- Do not expose bootstrap functionality through an unauthenticated public API.
"""

import argparse
import getpass
import os
import re
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.password import (
    PasswordValidationError,
    hash_password,
    validate_password_strength,
)
from backend.arthlens.security.roles import Role

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$")


def bootstrap_admin(email: str, password: str, full_name: str = "System Administrator") -> int:
    clean_email = email.strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        print(f"Error: Invalid email format '{email}'.", file=sys.stderr)
        return 1

    try:
        validate_password_strength(password)
    except PasswordValidationError as exc:
        print(f"Error: Password strength check failed: {exc}", file=sys.stderr)
        return 1

    repo = PostgresUserRepository()

    # Rule: Prevent repeated bootstrap if an active administrator already exists
    if repo.count_active_admins() > 0:
        print(
            "Error: Bootstrap rejected. An active administrator already exists in the system.",
            file=sys.stderr,
        )
        return 2

    # Check if user with this email already exists
    existing = repo.get_by_email(clean_email)
    pwd_hash = hash_password(password)

    if existing:
        # Upgrade existing user to ADMIN
        user_id = existing["id"]
        repo.set_user_roles(user_id, [Role.ADMIN.value])
        repo.update_password(user_id, pwd_hash)
        repo.activate_user(user_id)
        print(f"Existing user '{clean_email}' successfully promoted to primary ADMIN.")
    else:
        user_id = repo.save({
            "email": clean_email,
            "password_hash": pwd_hash,
            "roles": [Role.ADMIN.value],
            "quota_counters": {
                "full_name": full_name,
                "is_active": True,
                "runs_today": 0,
                "cost_today": 0.0,
            },
        })
        print(f"Administrator account '{clean_email}' successfully bootstrapped (ID: {user_id}).")

    audit = get_audit_service()
    audit.record_event(
        actor=user_id,
        action="AUTH_BOOTSTRAP_ADMIN",
        target=f"user:{user_id}",
        payload={"email": clean_email},
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap initial ArthLens administrator.")
    parser.add_argument("--email", help="Administrator email (or set ADMIN_BOOTSTRAP_EMAIL env var)")
    parser.add_argument("--password", help="Administrator password (or set ADMIN_BOOTSTRAP_PASSWORD env var)")
    parser.add_argument("--name", default="System Administrator", help="Administrator full name")

    args = parser.parse_args()

    email = args.email or os.getenv("ADMIN_BOOTSTRAP_EMAIL")
    password = args.password or os.getenv("ADMIN_BOOTSTRAP_PASSWORD")

    if not email:
        try:
            email = input("Administrator email: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.", file=sys.stderr)
            return 1

    if not password:
        try:
            password = getpass.getpass("Administrator password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.", file=sys.stderr)
            return 1

    return bootstrap_admin(email, password, args.name)


if __name__ == "__main__":
    raise SystemExit(main())

