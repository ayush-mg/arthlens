"""
PostgreSQL-backed User Repository Implementation for ArthLens.

Authoritative Specification: ArthLens — Business Operating System & Decision Intelligence Platform.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.arthlens.domain.repositories import UserAlreadyExistsError, UserRepository
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import UserModel, UserRoleModel


def _to_uuid(val: Union[str, uuid.UUID]) -> uuid.UUID:
    """Deterministically convert a string or UUID object to a valid uuid.UUID."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class PostgresUserRepository(UserRepository):
    """PostgreSQL-backed implementation of UserRepository."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def create_user(self, user_data: Dict[str, Any]) -> str:
        """
        Create a new user record strictly without updating existing accounts.
        Enforces database unique constraint on email.
        """
        user_uuid = _to_uuid(user_data.get("id") or uuid.uuid4())
        with self._get_session() as session:
            model = UserModel(
                id=user_uuid,
                email=user_data["email"].strip().lower(),
                password_hash=user_data["password_hash"],
                email_verified=bool(user_data.get("email_verified", False)),
                google_sub=user_data.get("google_sub"),
                auth_provider=user_data.get("auth_provider", "local"),
                two_factor_enabled=bool(user_data.get("two_factor_enabled", True)),
                quota_counters=user_data.get("quota_counters", {"is_active": True}),
            )
            session.add(model)
            if "roles" in user_data:
                for role_id in user_data["roles"]:
                    session.add(UserRoleModel(user_id=user_uuid, role_id=str(role_id)))
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise UserAlreadyExistsError(
                    f"User with email '{user_data['email']}' already exists."
                ) from exc
            return str(user_uuid)

    def save(self, user_data: Dict[str, Any]) -> str:
        user_uuid = _to_uuid(user_data.get("id") or uuid.uuid4())
        with self._get_session() as session:
            existing = session.get(UserModel, user_uuid)
            if not existing and "email" in user_data:
                existing = session.execute(
                    select(UserModel).where(UserModel.email == user_data["email"])
                ).scalar_one_or_none()

            if existing:
                user_uuid = existing.id
                existing.email = user_data["email"]
                existing.password_hash = user_data["password_hash"]
                existing.quota_counters = user_data.get("quota_counters", {})
                for field in ("email_verified", "google_sub", "auth_provider", "two_factor_enabled"):
                    if field in user_data:
                        setattr(existing, field, user_data[field])
            else:
                existing = UserModel(
                    id=user_uuid,
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    email_verified=bool(user_data.get("email_verified", True)),
                    google_sub=user_data.get("google_sub"),
                    auth_provider=user_data.get("auth_provider", "local"),
                    two_factor_enabled=bool(user_data.get("two_factor_enabled", True)),
                    quota_counters=user_data.get("quota_counters", {}),
                )
                session.add(existing)

            # Synchronize roles if specified
            if "roles" in user_data:
                session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == user_uuid))
                for role_id in user_data["roles"]:
                    session.add(UserRoleModel(user_id=user_uuid, role_id=str(role_id)))

            session.commit()
            return str(user_uuid)

    def get_by_id(self, user_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return None
            roles = [r.id for r in (model.roles or [])]
            return {
                "id": str(model.id),
                "email": model.email,
                "password_hash": model.password_hash,
                "quota_counters": model.quota_counters,
                "roles": roles,
                "created_at": model.created_at,
                "email_verified": model.email_verified,
                "google_sub": model.google_sub,
                "auth_provider": model.auth_provider,
                "two_factor_enabled": model.two_factor_enabled,
            }

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.email == email)
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None
            roles = [r.id for r in (model.roles or [])]
            return {
                "id": str(model.id),
                "email": model.email,
                "password_hash": model.password_hash,
                "quota_counters": model.quota_counters,
                "roles": roles,
                "created_at": model.created_at,
                "email_verified": model.email_verified,
                "google_sub": model.google_sub,
                "auth_provider": model.auth_provider,
                "two_factor_enabled": model.two_factor_enabled,
            }

    def update_unverified_user(self, email: str, password_hash: str, full_name: str) -> Optional[str]:
        """Refresh credentials for a pending account without touching verified users."""
        with self._get_session() as session:
            model = session.execute(
                select(UserModel).where(UserModel.email == email.strip().lower()).with_for_update()
            ).scalar_one_or_none()
            if model is None or model.email_verified:
                return None
            model.password_hash = password_hash
            counters = dict(model.quota_counters or {})
            counters["full_name"] = full_name
            counters["is_active"] = True
            model.quota_counters = counters
            session.commit()
            return str(model.id)

    def set_email_verified(self, user_id: Union[str, uuid.UUID], verified: bool = True) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if model is None:
                return False
            model.email_verified = verified
            session.commit()
            return True

    def get_by_google_sub(self, google_sub: str) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            model = session.execute(select(UserModel).where(UserModel.google_sub == google_sub)).scalar_one_or_none()
            if model is None:
                return None
            roles = [role.id for role in (model.roles or [])]
            return {
                "id": str(model.id), "email": model.email, "password_hash": model.password_hash,
                "quota_counters": model.quota_counters, "roles": roles, "created_at": model.created_at,
                "email_verified": model.email_verified, "google_sub": model.google_sub,
                "auth_provider": model.auth_provider, "two_factor_enabled": model.two_factor_enabled,
            }

    def link_google_identity(self, user_id: Union[str, uuid.UUID], google_sub: str) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if model is None:
                return False
            model.google_sub = google_sub
            model.auth_provider = "google"
            model.email_verified = True
            session.commit()
            return True

    def increment_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_uuid).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise KeyError(f"User {user_id} not found.")
            counters = dict(model.quota_counters or {})
            counters["runs_today"] = counters.get("runs_today", 0) + runs
            counters["cost_today"] = round(float(counters.get("cost_today", 0.0)) + cost, 4)
            model.quota_counters = counters
            session.commit()
            return counters

    def check_and_reserve_quota(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
        max_runs: int = 50,
        max_cost: float = 5.0,
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_uuid).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise KeyError(f"User {user_id} not found.")
            counters = dict(model.quota_counters or {})
            current_runs = counters.get("runs_today", 0)
            current_cost = float(counters.get("cost_today", 0.0))

            if current_runs + runs > max_runs:
                return False, counters, f"Daily run quota exceeded ({max_runs} runs per day)."

            if current_cost + cost > max_cost:
                return False, counters, f"Daily budget cap exceeded (${max_cost:.2f} per day)."

            counters["runs_today"] = current_runs + runs
            counters["cost_today"] = round(current_cost + cost, 4)
            model.quota_counters = counters
            session.commit()
            return True, counters, None

    def refund_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 0,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_uuid).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise KeyError(f"User {user_id} not found.")
            counters = dict(model.quota_counters or {})
            counters["runs_today"] = max(0, counters.get("runs_today", 0) - runs)
            counters["cost_today"] = max(0.0, round(float(counters.get("cost_today", 0.0)) - cost, 4))
            model.quota_counters = counters
            session.commit()
            return counters

    def deactivate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["is_active"] = False
            counters["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            model.quota_counters = counters
            session.commit()
            return True

    def activate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["is_active"] = True
            model.quota_counters = counters
            session.commit()
            return True

    def set_user_roles(self, user_id: Union[str, uuid.UUID], roles: List[str]) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            model.quota_counters = counters
            session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == user_uuid))
            for r_id in roles:
                session.add(UserRoleModel(user_id=user_uuid, role_id=str(r_id)))
            session.commit()
            return True

    def count_active_admins(self) -> int:
        with self._get_session() as session:
            stmt = (
                select(func.count(UserModel.id))
                .join(UserRoleModel, UserModel.id == UserRoleModel.user_id)
                .where(
                    UserRoleModel.role_id == "ADMIN",
                    func.coalesce(UserModel.quota_counters["is_active"].astext, "true") != "false",
                )
            )
            return session.execute(stmt).scalar() or 0

    def update_password(self, user_id: Union[str, uuid.UUID], password_hash: str) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            model.quota_counters = counters
            model.password_hash = password_hash
            session.commit()
            return True

    def set_password_reset_token(
        self,
        user_id: Union[str, uuid.UUID],
        token_hash: str,
        expires_at: datetime,
    ) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["password_reset"] = {
                "token_hash": token_hash,
                "expires_at": expires_at.isoformat(),
                "used": False,
            }
            model.quota_counters = counters
            session.commit()
            return True

    def verify_and_consume_password_reset(
        self,
        token_hash: str,
        new_password_hash: str,
    ) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(UserModel).where(
                UserModel.quota_counters["password_reset"]["token_hash"].astext == token_hash
            ).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None

            counters = dict(model.quota_counters or {})
            reset_info = dict(counters.get("password_reset") or {})
            if reset_info.get("used") is True:
                return None

            exp_str = reset_info.get("expires_at")
            if not exp_str:
                return None

            try:
                exp_dt = datetime.fromisoformat(exp_str)
                now = datetime.now(timezone.utc)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if now > exp_dt:
                    return None
            except Exception:
                return None

            # Mark token as single-use consumed
            reset_info["used"] = True
            counters["password_reset"] = reset_info
            # Invalidate all prior active sessions
            now_iso = datetime.now(timezone.utc).isoformat()
            counters["token_valid_after"] = now_iso
            model.quota_counters = counters
            model.password_hash = new_password_hash
            session.commit()

            roles = [r.id for r in (model.roles or [])]
            return {
                "id": str(model.id),
                "email": model.email,
                "roles": roles,
            }


__all__ = ["PostgresUserRepository"]
