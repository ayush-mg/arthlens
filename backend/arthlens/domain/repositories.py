"""
Domain Repository Interfaces and Persistence Exceptions for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Union
import uuid

from backend.arthlens.domain.interfaces import Repository
from backend.arthlens.domain.quantity import Quantity


class RepositoryError(Exception):
    """Base exception for persistence and repository operations."""
    pass


class QuantityNotFoundError(RepositoryError):
    """Raised when a requested Quantity cannot be located in the repository."""
    pass


class ImmutableQuantityError(RepositoryError):
    """
    Raised when an attempt is made to mutate the value or kind of an existing Quantity.

    Handbook Section 9.2:
        'Quantities are immutable: never UPDATE value or kind.
        Corrections create a new quantity and mark the old one superseded in quality_flags.'
    """
    pass


class QuantityRepository(Repository):
    """
    Abstract repository contract for Epistemic Ledger Quantities.

    Satisfies identical contracts across PostgreSQL and In-Memory implementations.
    """

    @abstractmethod
    def save(self, quantity: Quantity) -> None:
        """
        Persist a Quantity aggregate.

        If a Quantity with the same ID already exists:
        - If value or kind differs, raises ImmutableQuantityError.
        - If value and kind match, allows idempotent persistence / metadata update.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, quantity_id: Union[str, uuid.UUID]) -> Optional[Quantity]:
        """Retrieve a Quantity by its identifier, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, quantity_id: Union[str, uuid.UUID]) -> bool:
        """Return True if a Quantity with the given identifier exists, else False."""
        raise NotImplementedError

    @abstractmethod
    def list_by_definition(self, definition_key: str) -> List[Quantity]:
        """Retrieve all Quantities matching a definition key (e.g., 'population.total')."""
        raise NotImplementedError

    @abstractmethod
    def list_by_geo_unit(self, geo_unit_id: str) -> List[Quantity]:
        """Retrieve all Quantities for a specific geographic unit."""
        raise NotImplementedError

    @abstractmethod
    def get_parents(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        """Retrieve the immediate parent Quantities referenced in parent_ids."""
        raise NotImplementedError

    @abstractmethod
    def get_children(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        """
        Retrieve all direct child Quantities in the DAG whose parent_ids contain quantity_id.
        In PostgreSQL, this leverages the GIN index on parent_ids.
        """
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[Quantity]:
        """List all Quantities currently stored in the repository."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return the total number of Quantities stored."""
        raise NotImplementedError


class UserRepository(Repository):
    """Abstract repository contract for user accounts and role mappings."""

    @abstractmethod
    def save(self, user_data: Dict[str, Any]) -> str:
        """Save a user record and return its UUID string."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        """Retrieve user record by UUID, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user record by email, or None if not found."""
        raise NotImplementedError


class PolicyRuleRepository(Repository):
    """Abstract repository contract for policy documents and AST rules."""

    @abstractmethod
    def save_rule(self, rule_data: Dict[str, Any]) -> str:
        """Save a policy rule AST record and return its UUID string."""
        raise NotImplementedError

    @abstractmethod
    def get_rule(self, rule_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        """Retrieve rule by UUID, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def list_rules_by_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        """List all rules for a given scheme (e.g. 'pmfme')."""
        raise NotImplementedError


class ScenarioRepository(Repository):
    """Abstract repository contract for user scenarios and simulation runs."""

    @abstractmethod
    def save_scenario(self, scenario_data: Dict[str, Any]) -> str:
        """Save a user scenario and return its UUID string."""
        raise NotImplementedError

    @abstractmethod
    def get_scenario(self, scenario_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        """Retrieve scenario by UUID, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def list_by_owner(self, owner_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
        """List all scenarios owned by a user."""
        raise NotImplementedError

    @abstractmethod
    def save_simulation_run(self, run_data: Dict[str, Any]) -> str:
        """Save a simulation run record and return its UUID string."""
        raise NotImplementedError

    @abstractmethod
    def get_simulation_run(self, run_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        """Retrieve a simulation run record by UUID, or None if not found."""
        raise NotImplementedError
