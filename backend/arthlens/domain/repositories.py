"""
Domain Repository Interfaces and Persistence Exceptions for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Union
import uuid

from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import GeoUnit
from backend.arthlens.domain.interfaces import Repository
from backend.arthlens.domain.quantity import Quantity


class RepositoryError(Exception):
    """Base exception for persistence and repository operations."""
    pass


class ConflictingGeoUnitError(RepositoryError):
    """Raised when saving a geographic unit that conflicts with an existing unit."""
    pass


class OrphanedGeoUnitError(RepositoryError):
    """Raised when attempting to save a geographic unit whose parent entity does not exist."""
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
        """
        Atomically verify that incrementing (runs, cost) will not exceed (max_runs, max_cost).
        If within limits, reserves quota and returns (True, updated_counters, None).
        If exceeding limits, does NOT increment and returns (False, current_counters, reason).
        """
        raise NotImplementedError

    @abstractmethod
    def refund_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 0,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        """Atomically refund reserved runs or cost upon run cancellation or setup failure."""
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

    @abstractmethod
    def get_run_by_id_and_owner(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a simulation run only if owned by owner_id (IDOR defense)."""
        raise NotImplementedError

    @abstractmethod
    def get_scenario_by_id_and_owner(
        self,
        scenario_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a scenario only if owned by owner_id (IDOR defense)."""
        raise NotImplementedError


class SourceRepository(Repository):
    """Abstract repository for registered external data sources and snapshot versions."""

    @abstractmethod
    def save_source(self, source_data: Dict[str, Any]) -> None:
        """Upsert a registered data source record."""
        raise NotImplementedError

    @abstractmethod
    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve source metadata by source ID."""
        raise NotImplementedError

    @abstractmethod
    def save_version(self, version_data: Dict[str, Any]) -> str:
        """Save a source snapshot version idempotently and return its version ID."""
        raise NotImplementedError

    @abstractmethod
    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific source version by its version ID."""
        raise NotImplementedError

    @abstractmethod
    def get_version_by_hash(self, source_id: str, content_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve a source version matching a specific content hash for snapshot idempotency."""
        raise NotImplementedError

    @abstractmethod
    def list_versions(self, source_id: str) -> List[Dict[str, Any]]:
        """List all historical snapshot versions for a data source in descending chronological order."""
        raise NotImplementedError


class SourceRecordRepository(Repository):
    """Abstract repository for normalized records preserving raw and structured data."""

    @abstractmethod
    def save_record(self, record_data: Any) -> None:
        """Persist a single normalized source record idempotently."""
        raise NotImplementedError

    @abstractmethod
    def save_records(self, records: Sequence[Any]) -> int:
        """Persist a batch of normalized source records idempotently, returning count saved."""
        raise NotImplementedError

    @abstractmethod
    def get_record(self, source_version_id: str, record_id: str) -> Optional[Any]:
        """Retrieve a normalized record by version ID and record ID."""
        raise NotImplementedError

    @abstractmethod
    def list_by_version(self, source_version_id: str) -> List[Any]:
        """List all normalized records associated with a snapshot version."""
        raise NotImplementedError

    @abstractmethod
    def list_by_source(self, source_id: str) -> List[Any]:
        """List all normalized records across versions for a source ID."""
        raise NotImplementedError


class GeoUnitRepository(Repository):
    """Abstract repository for geographic administrative units and hierarchy."""

    @abstractmethod
    def save_unit(self, unit: GeoUnit) -> None:
        """Persist a single geographic unit. Validates parent existence and prevents duplicates."""
        raise NotImplementedError

    @abstractmethod
    def save_units(self, units: Sequence[GeoUnit]) -> int:
        """Persist a sequence of geographic units. Preserves topological parent-before-child ordering."""
        raise NotImplementedError

    @abstractmethod
    def get_unit(self, unit_id: str) -> Optional[GeoUnit]:
        """Retrieve a geographic unit by its canonical namespaced identifier."""
        raise NotImplementedError

    @abstractmethod
    def get_unit_by_lgd_code(self, level: ResolutionTier, lgd_code: str) -> Optional[GeoUnit]:
        """Retrieve a geographic unit by its administrative tier and raw LGD code."""
        raise NotImplementedError

    @abstractmethod
    def list_by_parent(self, parent_id: Optional[str]) -> List[GeoUnit]:
        """List immediate child geographic units for a given parent identifier (or root units if None)."""
        raise NotImplementedError

    @abstractmethod
    def list_by_level(self, level: ResolutionTier) -> List[GeoUnit]:
        """List all geographic units at a specific administrative tier."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, limit: int = 50) -> List[GeoUnit]:
        """Search geographic units by name (case-insensitive substring match)."""
        raise NotImplementedError
