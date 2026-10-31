"""
Roles Definition for ArthLens Role-Based Access Control (RBAC).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from enum import Enum


class Role(str, Enum):
    """
    Authoritative MVP roles specified in Handbook Part 10.1.
    Future roles (INVESTOR, SUPPLIER, PROGRAMME_OFFICER) must not be prematurely added.
    """
    ENTREPRENEUR = "ENTREPRENEUR"
    STEWARD = "STEWARD"
    ADMIN = "ADMIN"


__all__ = ["Role"]
