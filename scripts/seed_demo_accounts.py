"""
Seed local development demo accounts.

Authoritative Specification: ArthLens Build Handbook Part 10.1, 11, 14.
Roles:
- ENTREPRENEUR: demo.entrepreneur@arthlens.local
- STEWARD: demo.steward@arthlens.local
- ADMIN: demo.admin@arthlens.local
"""

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role

DEMO_ACCOUNTS = [
    {
        "email": "demo.entrepreneur@arthlens.local",
        "name": "Demo Entrepreneur",
        "role": Role.ENTREPRENEUR.value,
        "default_pwd": "Entrepreneur123!",
        "env_var": "DEMO_ENTREPRENEUR_PASSWORD",
    },
    {
        "email": "demo.steward@arthlens.local",
        "name": "Demo Steward",
        "role": Role.STEWARD.value,
        "default_pwd": "Steward123!",
        "env_var": "DEMO_STEWARD_PASSWORD",
    },
    {
        "email": "demo.admin@arthlens.local",
        "name": "Demo Administrator",
        "role": Role.ADMIN.value,
        "default_pwd": "Administrator123!",
        "env_var": "DEMO_ADMIN_PASSWORD",
    },
    {
        "email": "entrepreneur@arthlens.org",
        "name": "Dev Entrepreneur",
        "role": Role.ENTREPRENEUR.value,
        "default_pwd": "Password123!",
        "env_var": "DEV_ENTREPRENEUR_PASSWORD",
    },
    {
        "email": "steward@arthlens.org",
        "name": "Dev Steward",
        "role": Role.STEWARD.value,
        "default_pwd": "Password123!",
        "env_var": "DEV_STEWARD_PASSWORD",
    },
    {
        "email": "admin@arthlens.org",
        "name": "Dev Administrator",
        "role": Role.ADMIN.value,
        "default_pwd": "Password123!",
        "env_var": "DEV_ADMIN_PASSWORD",
    },
]


def seed_demo_accounts() -> int:
    repo = PostgresUserRepository()
    audit = get_audit_service()
    seeded = 0

    for account in DEMO_ACCOUNTS:
        email = account["email"]
        password = os.getenv(account["env_var"], account["default_pwd"])
        existing = repo.get_by_email(email)

        if existing:
            print(f"[SEED] Account already exists: {email} (Roles: {existing.get('roles')})")
            continue

        pwd_hash = hash_password(password)
        user_id = repo.save({
            "email": email,
            "password_hash": pwd_hash,
            "roles": [account["role"]],
            "quota_counters": {
                "full_name": account["name"],
                "is_active": True,
                "is_demo": True,
                "runs_today": 0,
                "cost_today": 0.0,
            },
        })
        audit.record_event(
            actor=user_id,
            action="AUTH_SEED_DEMO_ACCOUNT",
            target=f"user:{user_id}",
            payload={"email": email, "role": account["role"]},
        )
        print(f"[SEED] Created demo account: {email} as {account['role']} (ID: {user_id})")
        seeded += 1

    print(f"[SEED] Done. {seeded} new demo account(s) created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(seed_demo_accounts())

