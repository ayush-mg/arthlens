"""
PostgreSQL-backed Repository Implementations for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
import uuid

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import (
    ImmutableQuantityError,
    PolicyRuleRepository,
    QuantityNotFoundError,
    QuantityRepository,
    ScenarioRepository,
    UserRepository,
)
from backend.arthlens.domain.simulation import (
    MAX_UINT64,
    SimulationMetadata,
    validate_and_convert_seed,
)
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    PolicyRuleModel,
    QuantityModel,
    ScenarioModel,
    SimulationRunModel,
    UserModel,
    UserRoleModel,
)


def _to_uuid(val: Union[str, uuid.UUID]) -> uuid.UUID:
    """Deterministically convert a string or UUID object to a valid uuid.UUID."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))





class PostgresQuantityRepository(QuantityRepository):
    """
    PostgreSQL-backed implementation of QuantityRepository.

    Enforces immutable quantity semantics and persists full lineage, JSONB uncertainty,
    quality flags, and P1-4 SimulationMetadata.
    """

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def _to_model(self, q: Quantity) -> QuantityModel:
        """Convert a domain Quantity into a SQLAlchemy QuantityModel."""
        q_id = _to_uuid(q.id)
        kind_str = q.kind.value if isinstance(q.kind, Kind) else str(q.kind)

        # Parse date for as_of if string
        as_of_date = None
        if q.as_of:
            if isinstance(q.as_of, date):
                as_of_date = q.as_of
            elif isinstance(q.as_of, str):
                try:
                    as_of_date = date.fromisoformat(q.as_of)
                except ValueError:
                    as_of_date = None

        # Format parent_ids as UUID list for Postgres UUID[]
        parent_uuids = [_to_uuid(pid) for pid in q.parent_ids]

        # Format source_refs for JSONB
        source_refs_json = [
            list(ref) if isinstance(ref, (tuple, list)) else ref
            for ref in q.source_refs
        ]

        # Serialize SimulationMetadata if present
        sim_meta_json = None
        if q.simulation_meta is not None:
            sim_meta_json = {
                "scenario_id": q.simulation_meta.scenario_id,
                "model_version": q.simulation_meta.model_version,
                "seed": q.simulation_meta.seed,
                "sample_count": q.simulation_meta.sample_count,
                "data_versions": list(q.simulation_meta.data_versions),
            }

        return QuantityModel(
            id=q_id,
            definition_key=q.definition_key,
            value=float(q.value) if q.value is not None else None,
            unit=q.unit,
            kind=kind_str,
            evidence_floor=int(q.evidence_floor),
            geo_unit_id=q.geo_unit_id,
            resolution=int(q.resolution),
            as_of=as_of_date,
            uncertainty=q.uncertainty,
            source_refs=source_refs_json,
            method_id=q.method_id or "",
            model_version=q.model_version or "",
            parent_ids=parent_uuids,
            quality_flags=list(q.quality_flags),
            license_meta=q.license_meta or "",
            owner_id=_to_uuid(q.owner_id) if q.owner_id else None,
            simulation_meta=sim_meta_json,
        )

    def _from_model(self, m: QuantityModel) -> Quantity:
        """Reconstruct a domain Quantity from a SQLAlchemy QuantityModel."""
        # Restore kind enum
        kind_enum = Kind(m.kind)

        # Restore as_of string
        as_of_str = m.as_of.isoformat() if m.as_of is not None else ""

        # Restore parent_ids tuple of UUID strings
        parent_ids_tuple = tuple(str(pid) for pid in (m.parent_ids or []))

        # Restore quality_flags frozenset
        quality_flags_set = frozenset(m.quality_flags or [])

        # Restore source_refs tuple
        source_refs_tuple = tuple(
            tuple(item) if isinstance(item, list) else item
            for item in (m.source_refs or [])
        )

        # Restore SimulationMetadata if present
        sim_meta_obj = None
        if m.simulation_meta:
            sm = m.simulation_meta
            sim_meta_obj = SimulationMetadata(
                scenario_id=sm["scenario_id"],
                model_version=sm["model_version"],
                seed=int(sm["seed"]),
                sample_count=int(sm["sample_count"]),
                data_versions=tuple(sm.get("data_versions", ())),
            )

        return Quantity(
            id=str(m.id),
            definition_key=m.definition_key,
            value=float(m.value) if m.value is not None else 0.0,
            unit=m.unit,
            kind=kind_enum,
            evidence_floor=int(m.evidence_floor),
            geo_unit_id=m.geo_unit_id,
            resolution=int(m.resolution),
            as_of=as_of_str,
            uncertainty=m.uncertainty,
            source_refs=source_refs_tuple,
            method_id=m.method_id or "",
            model_version=m.model_version or "",
            parent_ids=parent_ids_tuple,
            quality_flags=quality_flags_set,
            license_meta=m.license_meta or "",
            simulation_meta=sim_meta_obj,
            owner_id=str(m.owner_id) if m.owner_id else None,
        )

    def save(self, quantity: Quantity) -> None:
        target_uuid = _to_uuid(quantity.id)
        kind_str = quantity.kind.value if isinstance(quantity.kind, Kind) else str(quantity.kind)

        with self._get_session() as session:
            existing = session.get(QuantityModel, target_uuid)
            if existing is not None:
                # Immutability check
                if existing.value != quantity.value or existing.kind != kind_str:
                    raise ImmutableQuantityError(
                        f"Quantity {quantity.id} is immutable: value ({existing.value} -> {quantity.value}) "
                        f"and kind ({existing.kind} -> {quantity.kind}) cannot be modified."
                    )
                # Idempotent update for non-immutable fields (e.g., superseding quality flags)
                existing.quality_flags = list(quantity.quality_flags)
                session.commit()
                return

            model = self._to_model(quantity)
            session.add(model)
            session.commit()

    def get(self, quantity_id: Union[str, uuid.UUID]) -> Optional[Quantity]:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            model = session.get(QuantityModel, target_uuid)
            if model is None:
                return None
            return self._from_model(model)

    def exists(self, quantity_id: Union[str, uuid.UUID]) -> bool:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            stmt = select(func.count()).select_from(QuantityModel).where(QuantityModel.id == target_uuid)
            return bool(session.execute(stmt).scalar() > 0)

    def list_by_definition(self, definition_key: str) -> List[Quantity]:
        with self._get_session() as session:
            stmt = select(QuantityModel).where(QuantityModel.definition_key == definition_key)
            models = session.execute(stmt).scalars().all()
            return [self._from_model(m) for m in models]

    def list_by_geo_unit(self, geo_unit_id: str) -> List[Quantity]:
        with self._get_session() as session:
            stmt = select(QuantityModel).where(QuantityModel.geo_unit_id == geo_unit_id)
            models = session.execute(stmt).scalars().all()
            return [self._from_model(m) for m in models]

    def get_parents(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            model = session.get(QuantityModel, target_uuid)
            if not model or not model.parent_ids:
                return []
            stmt = select(QuantityModel).where(QuantityModel.id.in_(model.parent_ids))
            parents = session.execute(stmt).scalars().all()
            return [self._from_model(p) for p in parents]

    def get_children(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            # Leverage Postgres GIN index on parent_ids with array containment
            stmt = select(QuantityModel).where(QuantityModel.parent_ids.contains([target_uuid]))
            children = session.execute(stmt).scalars().all()
            return [self._from_model(c) for c in children]

    def list_all(self) -> List[Quantity]:
        with self._get_session() as session:
            stmt = select(QuantityModel)
            models = session.execute(stmt).scalars().all()
            return [self._from_model(m) for m in models]

    def count(self) -> int:
        with self._get_session() as session:
            stmt = select(func.count()).select_from(QuantityModel)
            return int(session.execute(stmt).scalar() or 0)


class PostgresUserRepository(UserRepository):
    """PostgreSQL-backed implementation of UserRepository."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

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
            else:
                existing = UserModel(
                    id=user_uuid,
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
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
            }

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


class PostgresPolicyRuleRepository(PolicyRuleRepository):
    """PostgreSQL-backed implementation of PolicyRuleRepository."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def save_rule(self, rule_data: Dict[str, Any]) -> str:
        rule_uuid = _to_uuid(rule_data.get("id") or uuid.uuid4())
        with self._get_session() as session:
            existing = session.get(PolicyRuleModel, rule_uuid)
            if existing:
                existing.scheme_id = rule_data["scheme_id"]
                existing.version = rule_data["version"]
                existing.rule_ast = rule_data["rule_ast"]
                existing.status = rule_data.get("status", "DRAFT")
                session.commit()
                return str(rule_uuid)

            model = PolicyRuleModel(
                id=rule_uuid,
                scheme_id=rule_data["scheme_id"],
                version=rule_data["version"],
                rule_ast=rule_data["rule_ast"],
                status=rule_data.get("status", "DRAFT"),
            )
            session.add(model)
            session.commit()
            return str(rule_uuid)

    def get_rule(self, rule_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        rule_uuid = _to_uuid(rule_id)
        with self._get_session() as session:
            model = session.get(PolicyRuleModel, rule_uuid)
            if not model:
                return None
            return {
                "id": str(model.id),
                "scheme_id": model.scheme_id,
                "version": model.version,
                "rule_ast": model.rule_ast,
                "status": model.status,
                "created_at": model.created_at,
            }

    def list_rules_by_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(PolicyRuleModel).where(PolicyRuleModel.scheme_id == scheme_id)
            models = session.execute(stmt).scalars().all()
            return [
                {
                    "id": str(m.id),
                    "scheme_id": m.scheme_id,
                    "version": m.version,
                    "rule_ast": m.rule_ast,
                    "status": m.status,
                    "created_at": m.created_at,
                }
                for m in models
            ]


class PostgresScenarioRepository(ScenarioRepository):
    """PostgreSQL-backed implementation of ScenarioRepository."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def save_scenario(self, scenario_data: Dict[str, Any]) -> str:
        scenario_uuid = _to_uuid(scenario_data.get("id") or uuid.uuid4())
        owner_uuid = _to_uuid(scenario_data["owner_id"])
        with self._get_session() as session:
            existing = session.get(ScenarioModel, scenario_uuid)
            if existing:
                existing.name = scenario_data["name"]
                existing.scenario = scenario_data["scenario"]
                session.commit()
                return str(scenario_uuid)

            model = ScenarioModel(
                id=scenario_uuid,
                owner_id=owner_uuid,
                name=scenario_data["name"],
                scenario=scenario_data["scenario"],
            )
            session.add(model)
            session.commit()
            return str(scenario_uuid)

    def get_scenario(self, scenario_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        scenario_uuid = _to_uuid(scenario_id)
        with self._get_session() as session:
            model = session.get(ScenarioModel, scenario_uuid)
            if not model:
                return None
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "name": model.name,
                "scenario": model.scenario,
                "created_at": model.created_at,
            }

    def list_by_owner(self, owner_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            stmt = select(ScenarioModel).where(ScenarioModel.owner_id == owner_uuid)
            models = session.execute(stmt).scalars().all()
            return [
                {
                    "id": str(m.id),
                    "owner_id": str(m.owner_id),
                    "name": m.name,
                    "scenario": m.scenario,
                    "created_at": m.created_at,
                }
                for m in models
            ]

    def save_simulation_run(self, run_data: Dict[str, Any]) -> str:
        run_uuid = _to_uuid(run_data.get("id") or uuid.uuid4())
        scenario_uuid = _to_uuid(run_data["scenario_id"])
        seed_decimal = validate_and_convert_seed(run_data["seed"])

        with self._get_session() as session:
            existing = session.get(SimulationRunModel, run_uuid)
            if existing:
                existing.seed = seed_decimal
                existing.model_version = run_data["model_version"]
                existing.git_hash = run_data.get("git_hash")
                existing.data_version_ids = list(run_data.get("data_version_ids", []))
                existing.outputs_references = run_data.get("outputs_references", {})
                existing.status = run_data.get("status", "PENDING")
                session.commit()
                return str(run_uuid)

            model = SimulationRunModel(
                id=run_uuid,
                scenario_id=scenario_uuid,
                seed=seed_decimal,
                model_version=run_data["model_version"],
                git_hash=run_data.get("git_hash"),
                data_version_ids=list(run_data.get("data_version_ids", [])),
                outputs_references=run_data.get("outputs_references", {}),
                status=run_data.get("status", "PENDING"),
            )
            session.add(model)
            session.commit()
            return str(run_uuid)

    def get_simulation_run(self, run_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        run_uuid = _to_uuid(run_id)
        with self._get_session() as session:
            model = session.get(SimulationRunModel, run_uuid)
            if not model:
                return None
            seed_int = int(model.seed)
            return {
                "id": str(model.id),
                "scenario_id": str(model.scenario_id),
                "seed": seed_int,
                "model_version": model.model_version,
                "git_hash": model.git_hash,
                "data_version_ids": list(model.data_version_ids or []),
                "outputs_references": model.outputs_references,
                "status": model.status,
                "created_at": model.created_at,
            }

    def get_run_by_id_and_owner(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        run_uuid = _to_uuid(run_id)
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            stmt = (
                select(SimulationRunModel)
                .join(ScenarioModel, SimulationRunModel.scenario_id == ScenarioModel.id)
                .where(SimulationRunModel.id == run_uuid, ScenarioModel.owner_id == owner_uuid)
            )
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None
            seed_int = int(model.seed)
            return {
                "id": str(model.id),
                "scenario_id": str(model.scenario_id),
                "seed": seed_int,
                "model_version": model.model_version,
                "git_hash": model.git_hash,
                "data_version_ids": list(model.data_version_ids or []),
                "outputs_references": model.outputs_references,
                "status": model.status,
                "created_at": model.created_at,
            }

    def get_scenario_by_id_and_owner(
        self,
        scenario_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        scenario_uuid = _to_uuid(scenario_id)
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            stmt = select(ScenarioModel).where(
                ScenarioModel.id == scenario_uuid,
                ScenarioModel.owner_id == owner_uuid,
            )
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "name": model.name,
                "scenario": model.scenario,
                "created_at": model.created_at,
            }
