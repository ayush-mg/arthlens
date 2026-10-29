"""
In-Memory Repository Implementations for Offline Unit and Contract Testing.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

from typing import Any, Dict, List, Optional, Union
import uuid

from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import (
    ImmutableQuantityError,
    PolicyRuleRepository,
    QuantityRepository,
    ScenarioRepository,
    UserRepository,
)
from backend.arthlens.domain.simulation import validate_and_convert_seed


class InMemoryQuantityRepository(QuantityRepository):
    """
    In-memory fake implementation of QuantityRepository.

    Adheres strictly to the identical immutability and lineage contract as Postgres.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Quantity] = {}

    def _normalize_id(self, quantity_id: Union[str, uuid.UUID]) -> str:
        return str(quantity_id)

    def save(self, quantity: Quantity) -> None:
        key = self._normalize_id(quantity.id)
        if key in self._store:
            existing = self._store[key]
            # Enforce immutability of value and kind
            if existing.value != quantity.value or existing.kind != quantity.kind:
                raise ImmutableQuantityError(
                    f"Quantity {quantity.id} is immutable: value ({existing.value} -> {quantity.value}) "
                    f"and kind ({existing.kind} -> {quantity.kind}) cannot be modified."
                )
        self._store[key] = quantity

    def get(self, quantity_id: Union[str, uuid.UUID]) -> Optional[Quantity]:
        return self._store.get(self._normalize_id(quantity_id))

    def exists(self, quantity_id: Union[str, uuid.UUID]) -> bool:
        return self._normalize_id(quantity_id) in self._store

    def list_by_definition(self, definition_key: str) -> List[Quantity]:
        return [q for q in self._store.values() if q.definition_key == definition_key]

    def list_by_geo_unit(self, geo_unit_id: str) -> List[Quantity]:
        return [q for q in self._store.values() if q.geo_unit_id == geo_unit_id]

    def get_parents(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        q = self.get(quantity_id)
        if not q or not q.parent_ids:
            return []
        parents = []
        for pid in q.parent_ids:
            parent = self.get(pid)
            if parent is not None:
                parents.append(parent)
        return parents

    def get_children(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        target = self._normalize_id(quantity_id)
        children = []
        for q in self._store.values():
            if any(self._normalize_id(pid) == target for pid in q.parent_ids):
                children.append(q)
        return children

    def list_all(self) -> List[Quantity]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        """Reset the in-memory store between isolated tests."""
        self._store.clear()


class InMemoryUserRepository(UserRepository):
    """In-memory fake implementation of UserRepository."""

    def __init__(self) -> None:
        self._users: Dict[str, Dict[str, Any]] = {}

    def save(self, user_data: Dict[str, Any]) -> str:
        user_id = str(user_data.get("id") or uuid.uuid4())
        record = dict(user_data)
        record["id"] = user_id
        record.setdefault("quota_counters", {})
        self._users[user_id] = record
        return user_id

    def get_by_id(self, user_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        return self._users.get(str(user_id))

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        for u in self._users.values():
            if u.get("email") == email:
                return u
        return None

    def clear(self) -> None:
        self._users.clear()


class InMemoryPolicyRuleRepository(PolicyRuleRepository):
    """In-memory fake implementation of PolicyRuleRepository."""

    def __init__(self) -> None:
        self._rules: Dict[str, Dict[str, Any]] = {}

    def save_rule(self, rule_data: Dict[str, Any]) -> str:
        rule_id = str(rule_data.get("id") or uuid.uuid4())
        record = dict(rule_data)
        record["id"] = rule_id
        record.setdefault("status", "DRAFT")
        self._rules[rule_id] = record
        return rule_id

    def get_rule(self, rule_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        return self._rules.get(str(rule_id))

    def list_rules_by_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        return [r for r in self._rules.values() if r.get("scheme_id") == scheme_id]

    def clear(self) -> None:
        self._rules.clear()


class InMemoryScenarioRepository(ScenarioRepository):
    """In-memory fake implementation of ScenarioRepository."""

    def __init__(self) -> None:
        self._scenarios: Dict[str, Dict[str, Any]] = {}
        self._simulation_runs: Dict[str, Dict[str, Any]] = {}

    def save_scenario(self, scenario_data: Dict[str, Any]) -> str:
        scenario_id = str(scenario_data.get("id") or uuid.uuid4())
        record = dict(scenario_data)
        record["id"] = scenario_id
        self._scenarios[scenario_id] = record
        return scenario_id

    def get_scenario(self, scenario_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        return self._scenarios.get(str(scenario_id))

    def list_by_owner(self, owner_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
        owner_str = str(owner_id)
        return [s for s in self._scenarios.values() if str(s.get("owner_id")) == owner_str]

    def save_simulation_run(self, run_data: Dict[str, Any]) -> str:
        run_id = str(run_data.get("id") or uuid.uuid4())
        record = dict(run_data)
        record["id"] = run_id
        seed_decimal = validate_and_convert_seed(run_data["seed"])
        record["seed"] = int(seed_decimal)
        record.setdefault("status", "PENDING")
        self._simulation_runs[run_id] = record
        return run_id

    def get_simulation_run(self, run_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        return self._simulation_runs.get(str(run_id))

    def clear(self) -> None:
        self._scenarios.clear()
        self._simulation_runs.clear()
