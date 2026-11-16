"""
Domain Repository Interfaces for ArthLens.

Authoritative Specification: ArthLens — Business Operating System & Decision Intelligence Platform.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


class RepositoryError(Exception):
    """Base exception for persistence and repository operations."""
    pass


class UserAlreadyExistsError(RepositoryError):
    """Raised when attempting to create a user whose ID or email already exists."""
    pass


class UserRepository(ABC):
    """Abstract repository contract for user accounts and role mappings."""

    @abstractmethod
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user record strictly without updating existing accounts."""
        raise NotImplementedError

    @abstractmethod
    def save(self, user_data: Dict[str, Any]) -> str:
        """Save a user record (insert or update) and return its UUID string."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        """Retrieve user record by UUID, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user record by email, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def increment_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        """Atomically increment run count and cost for a user, returning updated counters."""
        raise NotImplementedError

    @abstractmethod
    def check_and_reserve_quota(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
        max_runs: int = 50,
        max_cost: float = 5.0,
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """Atomically verify that incrementing quota will not exceed limits."""
        raise NotImplementedError

    @abstractmethod
    def refund_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 0,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        """Atomically refund reserved quota."""
        raise NotImplementedError

    @abstractmethod
    def deactivate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        """Deactivate user account."""
        raise NotImplementedError

    @abstractmethod
    def activate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        """Activate user account."""
        raise NotImplementedError

    @abstractmethod
    def set_user_roles(self, user_id: Union[str, uuid.UUID], roles: List[str]) -> bool:
        """Set roles for user."""
        raise NotImplementedError

    @abstractmethod
    def count_active_admins(self) -> int:
        """Count number of active administrators."""
        raise NotImplementedError

    @abstractmethod
    def update_password(self, user_id: Union[str, uuid.UUID], password_hash: str) -> bool:
        """Update password hash for a user."""
        raise NotImplementedError

    @abstractmethod
    def set_password_reset_token(
        self,
        user_id: Union[str, uuid.UUID],
        token_hash: str,
        expires_at: datetime,
    ) -> bool:
        """Store an expiring, single-use password reset token hash for user."""
        raise NotImplementedError

    @abstractmethod
    def verify_and_consume_password_reset(
        self,
        token_hash: str,
        new_password_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Verify and consume single-use password reset token."""
        raise NotImplementedError
