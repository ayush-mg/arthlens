"""
In-Memory Repository Implementations for Offline Unit and Contract Testing.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

import threading
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.geo import GeometryStatus, GeoUnit
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import (
    ConflictingGeoUnitError,
    GeoUnitRepository,
    ImmutableQuantityError,
    OrphanedGeoUnitError,
    PolicyRuleRepository,
    QuantityRepository,
    ScenarioRepository,
    SourceRecordRepository,
    SourceRepository,
    UserAlreadyExistsError,
    UserRepository,
)
from backend.arthlens.domain.simulation import validate_and_convert_seed

GEOMETRY_STATUS_RANK: Dict[str, int] = {
    GeometryStatus.GEOMETRY_VERIFIED.value: 4,
    GeometryStatus.GEOMETRY_HISTORICAL.value: 3,
    GeometryStatus.GEOMETRY_SIMPLIFIED.value: 2,
    GeometryStatus.GEOMETRY_UNVALIDATED.value: 1,
    GeometryStatus.GEOMETRY_MISSING.value: 0,
}


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
        if len(set(quantity.parent_ids)) != len(quantity.parent_ids):
            raise ValueError(f"Duplicate parent references rejected for Quantity '{quantity.id}'.")
        missing_parents = {
            self._normalize_id(parent_id)
            for parent_id in quantity.parent_ids
            if self._normalize_id(parent_id) not in self._store
        }
        if missing_parents:
            raise ValueError(
                f"Quantity '{quantity.id}' references unregistered parent quantities: "
                f"{sorted(missing_parents)}."
            )
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
        self._lock = threading.Lock()

    def create_user(self, user_data: Dict[str, Any]) -> str:
        with self._lock:
            user_id = str(user_data.get("id") or uuid.uuid4())
            email = user_data["email"].strip().lower()
            if user_id in self._users or any(u.get("email") == email for u in self._users.values()):
                raise UserAlreadyExistsError(f"User with email '{email}' already exists.")
            record = dict(user_data)
            record["id"] = user_id
            record["email"] = email
            record.setdefault("quota_counters", {"is_active": True})
            record["roles"] = list(user_data.get("roles", []))
            self._users[user_id] = record
            return user_id

    def save(self, user_data: Dict[str, Any]) -> str:
        user_id = str(user_data.get("id") or uuid.uuid4())
        record = dict(user_data)
        record["id"] = user_id
        record.setdefault("quota_counters", {})
        record["roles"] = list(user_data.get("roles", []))
        self._users[user_id] = record
        return user_id

    def get_by_id(self, user_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        return self._users.get(str(user_id))

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        for u in self._users.values():
            if u.get("email") == email:
                return u
        return None

    def increment_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                raise KeyError(f"User {user_id} not found.")
            qc = dict(u.get("quota_counters", {}))
            qc["runs_today"] = qc.get("runs_today", 0) + runs
            qc["cost_today"] = round(float(qc.get("cost_today", 0.0)) + cost, 4)
            u["quota_counters"] = qc
            return qc

    def check_and_reserve_quota(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
        max_runs: int = 50,
        max_cost: float = 5.0,
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                raise KeyError(f"User {user_id} not found.")
            qc = dict(u.get("quota_counters", {}))
            current_runs = qc.get("runs_today", 0)
            current_cost = float(qc.get("cost_today", 0.0))

            if current_runs + runs > max_runs:
                return False, qc, f"Daily run quota exceeded ({max_runs} runs per day)."

            if current_cost + cost > max_cost:
                return False, qc, f"Daily budget cap exceeded (${max_cost:.2f} per day)."

            qc["runs_today"] = current_runs + runs
            qc["cost_today"] = round(current_cost + cost, 4)
            u["quota_counters"] = qc
            return True, qc, None

    def refund_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 0,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                raise KeyError(f"User {user_id} not found.")
            qc = dict(u.get("quota_counters", {}))
            qc["runs_today"] = max(0, qc.get("runs_today", 0) - runs)
            qc["cost_today"] = max(0.0, round(float(qc.get("cost_today", 0.0)) - cost, 4))
            u["quota_counters"] = qc
            return qc

    def deactivate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                return False
            qc = dict(u.get("quota_counters", {}))
            qc["is_active"] = False
            qc["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            u["quota_counters"] = qc
            return True

    def activate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                return False
            qc = dict(u.get("quota_counters", {}))
            qc["is_active"] = True
            u["quota_counters"] = qc
            return True

    def set_user_roles(self, user_id: Union[str, uuid.UUID], roles: List[str]) -> bool:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                return False
            qc = dict(u.get("quota_counters", {}))
            qc["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            u["quota_counters"] = qc
            u["roles"] = list(roles)
            return True

    def count_active_admins(self) -> int:
        with self._lock:
            count = 0
            for u in self._users.values():
                if "ADMIN" in u.get("roles", []) and u.get("quota_counters", {}).get("is_active", True) is not False:
                    count += 1
            return count

    def update_password(self, user_id: Union[str, uuid.UUID], password_hash: str) -> bool:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                return False
            qc = dict(u.get("quota_counters", {}))
            qc["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            u["quota_counters"] = qc
            u["password_hash"] = password_hash
            return True

    def set_password_reset_token(
        self,
        user_id: Union[str, uuid.UUID],
        token_hash: str,
        expires_at: datetime,
    ) -> bool:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                return False
            qc = dict(u.get("quota_counters", {}))
            qc["password_reset"] = {
                "token_hash": token_hash,
                "expires_at": expires_at.isoformat(),
                "used": False,
            }
            u["quota_counters"] = qc
            return True

    def verify_and_consume_password_reset(
        self,
        token_hash: str,
        new_password_hash: str,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            target_user = None
            for u in self._users.values():
                reset_info = u.get("quota_counters", {}).get("password_reset", {})
                if reset_info.get("token_hash") == token_hash:
                    target_user = u
                    break
            if not target_user:
                return None

            qc = dict(target_user.get("quota_counters", {}))
            reset_info = dict(qc.get("password_reset") or {})
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

            reset_info["used"] = True
            qc["password_reset"] = reset_info
            qc["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            target_user["quota_counters"] = qc
            target_user["password_hash"] = new_password_hash
            return {
                "id": target_user["id"],
                "email": target_user["email"],
                "roles": list(target_user.get("roles", [])),
            }

    def clear(self) -> None:
        self._users.clear()


class InMemoryPolicyRuleRepository(PolicyRuleRepository):
    """In-memory fake implementation of PolicyRuleRepository."""

    def __init__(self) -> None:
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._evaluations: Dict[str, Dict[str, Any]] = {}

    def save_document(self, document_data: Dict[str, Any]) -> str:
        document_id = str(document_data.get("id") or uuid.uuid4())
        if document_id in self._documents:
            raise ValueError("Policy documents are immutable; register a new source-version document.")
        if not all(document_data.get(field) for field in ("scheme_id", "source_version_id", "document_url", "sha256")):
            raise ValueError("Policy documents require a scheme and exact source-version metadata.")
        record = dict(document_data)
        record.update({"id": document_id, "status": "PENDING_REVIEW", "verified_by": None, "verified_at": None})
        self._documents[document_id] = record
        return document_id

    def get_document(self, document_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        record = self._documents.get(str(document_id))
        return dict(record) if record else None

    def review_document(
        self,
        document_id: Union[str, uuid.UUID],
        *,
        reviewer_id: Union[str, uuid.UUID],
        verified: bool,
        review_note: str,
    ) -> Optional[Dict[str, Any]]:
        record = self._documents.get(str(document_id))
        if record is None:
            return None
        if record["status"] != "PENDING_REVIEW":
            raise ValueError("Only a pending policy document can receive its first steward review.")
        record.update({
            "status": "VERIFIED" if verified else "REJECTED",
            "verified_by": str(reviewer_id),
            "verified_at": datetime.now(timezone.utc).isoformat() if verified else None,
            "review_note": review_note.strip(),
        })
        return dict(record)

    def save_rule(self, rule_data: Dict[str, Any]) -> str:
        rule_id = str(rule_data.get("id") or uuid.uuid4())
        if rule_id in self._rules:
            raise ValueError("Policy rule versions are immutable; create a new version key.")
        required = ("scheme_id", "rule_key", "version", "rule_ast", "evidence_requirements", "source_references", "effective_from")
        if any(rule_data.get(field) in (None, "", [], {}) for field in required if field != "evidence_requirements"):
            raise ValueError("Policy drafts require a key, version, AST, citations, and effective date.")
        if not isinstance(rule_data.get("evidence_requirements"), dict):
            raise ValueError("Policy evidence requirements must be an object keyed by each AST fact.")
        from backend.arthlens.policy.serialization import (
            parse_rule_ast,
            rule_facts,
            serialize_rule_ast,
        )

        try:
            node = parse_rule_ast(rule_data["rule_ast"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Policy rule AST is invalid: {exc}") from exc
        evidence_requirements = rule_data["evidence_requirements"]
        if rule_facts(node) != frozenset(evidence_requirements):
            raise ValueError("Policy evidence requirements must map exactly to every AST predicate fact.")
        valid_kinds = {kind.value for kind in Kind}
        for fact, requirement in evidence_requirements.items():
            if not isinstance(requirement, dict):
                raise ValueError(f"Evidence requirement for {fact!r} must be an object.")
            kinds = requirement.get("allowed_kinds")
            floor = requirement.get("minimum_evidence_floor")
            if (
                not requirement.get("definition_key")
                or not requirement.get("unit")
                or not isinstance(kinds, list)
                or not kinds
                or not all(isinstance(kind, str) for kind in kinds)
                or len(kinds) != len(set(kinds))
                or not set(kinds) <= valid_kinds
                or not isinstance(floor, int)
                or not 1 <= floor <= 4
            ):
                raise ValueError(f"Evidence requirement for {fact!r} is incomplete or invalid.")
        for citation in rule_data["source_references"]:
            document = self._documents.get(str(citation.get("document_id")))
            if (
                document is None
                or document.get("scheme_id") != rule_data["scheme_id"]
                or citation.get("source_version_id") != document.get("source_version_id")
                or citation.get("document_url") != document.get("document_url")
                or citation.get("sha256") != document.get("sha256")
                or not str(citation.get("locator") or "").strip()
            ):
                raise ValueError("Every citation must match a registered source document and locator.")
        if any(
            existing.get("scheme_id") == rule_data["scheme_id"]
            and existing.get("rule_key") == rule_data["rule_key"]
            and existing.get("version") == rule_data["version"]
            for existing in self._rules.values()
        ):
            raise ValueError("This scheme rule version already exists; policy versions are immutable.")
        record = dict(rule_data)
        record["rule_ast"] = serialize_rule_ast(node)
        record["id"] = rule_id
        record["status"] = "DRAFT"
        self._rules[rule_id] = record
        return rule_id

    def get_rule(self, rule_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        record = self._rules.get(str(rule_id))
        return dict(record) if record else None

    def list_rules_by_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._rules.values() if r.get("scheme_id") == scheme_id]

    def approve_rule(
        self,
        rule_id: Union[str, uuid.UUID],
        *,
        steward_id: Union[str, uuid.UUID],
        approval_note: str,
    ) -> Optional[Dict[str, Any]]:
        rule = self._rules.get(str(rule_id))
        if rule is None:
            return None
        if rule["status"] != "DRAFT":
            raise ValueError("Only a draft policy rule version can be approved.")
        start = rule.get("effective_from")
        end = rule.get("effective_to")
        if start is None:
            raise ValueError("An effective_from date is required before approval.")
        if end is not None and end < start:
            raise ValueError("effective_to must not precede effective_from.")
        citations = rule.get("source_references") or []
        if not citations:
            raise ValueError("At least one exact source-version citation is required before approval.")
        for citation in citations:
            document = self._documents.get(str(citation.get("document_id")))
            if (
                document is None
                or document.get("scheme_id") != rule.get("scheme_id")
                or document.get("status") != "VERIFIED"
                or citation.get("source_version_id") != document.get("source_version_id")
                or citation.get("document_url") != document.get("document_url")
                or citation.get("sha256") != document.get("sha256")
            ):
                raise ValueError("Every cited document must be steward-verified and match its exact source version.")
        requested_to = end or date.max
        for other in self._rules.values():
            if other["id"] == rule["id"] or other["status"] != "APPROVED":
                continue
            if other.get("scheme_id") != rule.get("scheme_id") or other.get("rule_key") != rule.get("rule_key"):
                continue
            other_from = other.get("effective_from")
            other_to = other.get("effective_to") or date.max
            if other_from is not None and start <= other_to and other_from <= requested_to:
                raise ValueError("The effective period overlaps another approved version of this rule.")
        rule.update({
            "status": "APPROVED",
            "approved_by": str(steward_id),
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approval_note": approval_note.strip(),
        })
        return dict(rule)

    def retire_rule(
        self,
        rule_id: Union[str, uuid.UUID],
        *,
        steward_id: Union[str, uuid.UUID],
        retirement_reason: str,
    ) -> Optional[Dict[str, Any]]:
        rule = self._rules.get(str(rule_id))
        if rule is None:
            return None
        if rule["status"] != "APPROVED":
            raise ValueError("Only an approved policy rule version can be retired.")
        rule.update({
            "status": "RETIRED",
            "retired_by": str(steward_id),
            "retired_at": datetime.now(timezone.utc).isoformat(),
            "retirement_reason": retirement_reason.strip(),
        })
        return dict(rule)

    def get_applicable_rules(self, scheme_id: str, rule_key: str, as_of: Any) -> List[Dict[str, Any]]:
        if isinstance(as_of, str):
            as_of = date.fromisoformat(as_of)
        return [
            dict(rule) for rule in self._rules.values()
            if rule.get("scheme_id") == scheme_id
            and rule.get("rule_key") == rule_key
            and rule.get("status") == "APPROVED"
            and rule.get("effective_from") is not None
            and rule["effective_from"] <= as_of
            and (rule.get("effective_to") is None or rule["effective_to"] >= as_of)
        ]

    def save_evaluation(self, evaluation_data: Dict[str, Any]) -> str:
        evaluation_id = str(evaluation_data.get("id") or uuid.uuid4())
        record = dict(evaluation_data)
        record["id"] = evaluation_id
        self._evaluations[evaluation_id] = record
        return evaluation_id

    def get_evaluation(
        self,
        evaluation_id: Union[str, uuid.UUID],
        *,
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        record = self._evaluations.get(str(evaluation_id))
        if record is None or str(record.get("owner_id")) != str(owner_id):
            return None
        return dict(record)

    def clear(self) -> None:
        self._documents.clear()
        self._rules.clear()
        self._evaluations.clear()


class InMemoryScenarioRepository(ScenarioRepository):
    """In-memory fake implementation of ScenarioRepository."""

    def __init__(self) -> None:
        self._scenarios: Dict[str, Dict[str, Any]] = {}
        self._simulation_runs: Dict[str, Dict[str, Any]] = {}
        self._scenario_comparisons: Dict[str, Dict[str, Any]] = {}

    def save_scenario(self, scenario_data: Dict[str, Any]) -> str:
        scenario_id = str(scenario_data.get("id") or uuid.uuid4())
        existing = self._scenarios.get(scenario_id)
        if existing and str(existing.get("owner_id")) != str(scenario_data.get("owner_id")):
            raise PermissionError("Scenario records may only be updated by their owner.")
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

    def get_run_by_id_and_owner(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        run = self._simulation_runs.get(str(run_id))
        if not run:
            return None
        scenario = self._scenarios.get(str(run.get("scenario_id")))
        if scenario and str(scenario.get("owner_id")) == str(owner_id):
            return run
        return None

    def get_scenario_by_id_and_owner(
        self,
        scenario_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        scenario = self._scenarios.get(str(scenario_id))
        if scenario and str(scenario.get("owner_id")) == str(owner_id):
            return scenario
        return None

    def save_comparison(self, comparison_data: Dict[str, Any]) -> str:
        comparison_id = str(comparison_data.get("id") or uuid.uuid4())
        left_id = str(comparison_data["left_scenario_id"])
        right_id = str(comparison_data["right_scenario_id"])
        if left_id == right_id:
            raise ValueError("A scenario cannot be compared with itself.")
        if comparison_id in self._scenario_comparisons:
            raise ValueError("Scenario comparison records are immutable.")
        owner_id = str(comparison_data["owner_id"])
        if not self.get_scenario_by_id_and_owner(left_id, owner_id) or not self.get_scenario_by_id_and_owner(right_id, owner_id):
            raise ValueError("Both scenarios must exist and belong to the comparison owner.")
        record = dict(comparison_data)
        record["id"] = comparison_id
        self._scenario_comparisons[comparison_id] = record
        return comparison_id

    def get_comparison_by_id_and_owner(
        self,
        comparison_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        record = self._scenario_comparisons.get(str(comparison_id))
        if record is None or str(record.get("owner_id")) != str(owner_id):
            return None
        return dict(record)

    def delete_scenario(
        self,
        scenario_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> bool:
        s_id = str(scenario_id)
        scenario = self._scenarios.get(s_id)
        if scenario and str(scenario.get("owner_id")) == str(owner_id):
            del self._scenarios[s_id]
            return True
        return False

    def clear(self) -> None:
        self._scenarios.clear()
        self._simulation_runs.clear()
        self._scenario_comparisons.clear()


class InMemorySourceRepository(SourceRepository):
    """In-memory fake implementation of SourceRepository for testing."""

    def __init__(self) -> None:
        self._sources: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, Dict[str, Any]] = {}

    def save_source(self, source_data: Dict[str, Any]) -> None:
        s_id = str(source_data["id"])
        self._sources[s_id] = dict(source_data)

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        return self._sources.get(str(source_id))

    def save_version(self, version_data: Dict[str, Any]) -> str:
        s_id = str(version_data["source_id"])
        c_hash = str(version_data["content_hash"])

        # Check existing version by hash for idempotency
        for v in self._versions.values():
            if v.get("source_id") == s_id and v.get("content_hash") == c_hash:
                return v["id"]

        v_id = str(version_data.get("id") or f"{s_id}:{c_hash[:16]}")
        rec = dict(version_data)
        rec["id"] = v_id
        self._versions[v_id] = rec
        return v_id

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        return self._versions.get(str(version_id))

    def get_version_by_hash(self, source_id: str, content_hash: str) -> Optional[Dict[str, Any]]:
        for v in self._versions.values():
            if v.get("source_id") == str(source_id) and v.get("content_hash") == str(content_hash):
                return v
        return None

    def list_versions(self, source_id: str) -> List[Dict[str, Any]]:
        return [v for v in self._versions.values() if v.get("source_id") == str(source_id)]

    def clear(self) -> None:
        self._sources.clear()
        self._versions.clear()


class InMemorySourceRecordRepository(SourceRecordRepository):
    """In-memory fake implementation of SourceRecordRepository for testing."""

    def __init__(self) -> None:
        self._records: Dict[str, Any] = {}

    def _make_key(self, source_version_id: str, record_id: str) -> str:
        return f"{source_version_id}:{record_id}"

    def save_record(self, record: Any) -> None:
        key = self._make_key(record.source_version_id, record.record_id)
        self._records[key] = record

    def save_records(self, records: Sequence[Any]) -> int:
        count = 0
        for rec in records:
            key = self._make_key(rec.source_version_id, rec.record_id)
            if key not in self._records:
                count += 1
            self._records[key] = rec
        return count

    def get_record(self, source_version_id: str, record_id: str) -> Optional[Any]:
        return self._records.get(self._make_key(source_version_id, record_id))

    def list_by_version(self, source_version_id: str) -> List[Any]:
        return [r for r in self._records.values() if r.source_version_id == str(source_version_id)]

    def list_by_source(self, source_id: str) -> List[Any]:
        return [r for r in self._records.values() if r.source_id == str(source_id)]

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()


def _codes_differ(code1: Optional[str], code2: Optional[str]) -> bool:
    """Check if two codes differ, treating leading-zero numeric strings as matching."""
    if code1 == code2:
        return False
    if code1 is not None and code2 is not None:
        c1, c2 = str(code1).strip(), str(code2).strip()
        if c1.isdigit() and c2.isdigit():
            return int(c1) != int(c2)
    return True


class InMemoryGeoUnitRepository(GeoUnitRepository):
    """In-memory fake implementation of GeoUnitRepository for unit and contract testing."""

    def __init__(self) -> None:
        self._store: Dict[str, GeoUnit] = {}
        self._lock = threading.Lock()

    def save_unit(self, unit: GeoUnit) -> None:
        with self._lock:
            # Check parent existence
            if unit.parent_id is not None and unit.parent_id not in self._store:
                raise OrphanedGeoUnitError(
                    f"Parent unit '{unit.parent_id}' does not exist in repository for child '{unit.id}'."
                )

            # Check existing unit conflicts
            if unit.id in self._store:
                existing = self._store[unit.id]
                if (
                    existing.name != unit.name
                    or existing.level != unit.level
                    or _codes_differ(existing.lgd_code, unit.lgd_code)
                    or existing.parent_id != unit.parent_id
                ):
                    raise ConflictingGeoUnitError(
                        f"GeoUnit '{unit.id}' already exists with conflicting definition: "
                        f"existing (name={existing.name}, level={existing.level}, lgd={existing.lgd_code}), "
                        f"new (name={unit.name}, level={unit.level}, lgd={unit.lgd_code})."
                    )
                # Idempotent re-save of same entity; enrich if verified geometry or census code provided
                if unit.geometry is not None or (unit.census_code and not existing.census_code):
                    self._store[unit.id] = unit
                return

            self._store[unit.id] = unit

    def save_units(self, units: Sequence[GeoUnit]) -> int:
        with self._lock:
            # Staging dict to guarantee atomic batch application and complete rollback on failure
            staged = dict(self._store)
            count = 0
            for unit in units:
                if unit.parent_id is not None and unit.parent_id not in staged:
                    raise OrphanedGeoUnitError(
                        f"Parent unit '{unit.parent_id}' does not exist in repository for child '{unit.id}'."
                    )
                if unit.id in staged:
                    existing = staged[unit.id]
                    if (
                        existing.name != unit.name
                        or existing.level != unit.level
                        or _codes_differ(existing.lgd_code, unit.lgd_code)
                        or existing.parent_id != unit.parent_id
                    ):
                        raise ConflictingGeoUnitError(
                            f"GeoUnit '{unit.id}' already exists with conflicting definition: "
                            f"existing (name={existing.name}, level={existing.level}, lgd={existing.lgd_code}), "
                            f"new (name={unit.name}, level={unit.level}, lgd={unit.lgd_code})."
                        )
                    if unit.geometry is not None or (unit.census_code and not existing.census_code):
                        staged[unit.id] = unit
                    continue
                staged[unit.id] = unit
                count += 1
            # Commit atomic batch
            self._store = staged
            return count

    def get_unit(self, unit_id: str) -> Optional[GeoUnit]:
        with self._lock:
            return self._store.get(str(unit_id))

    def get_unit_by_lgd_code(self, level: ResolutionTier, lgd_code: str) -> Optional[GeoUnit]:
        with self._lock:
            target_code = str(lgd_code).strip()
            for u in self._store.values():
                if u.level == level and u.lgd_code == target_code:
                    return u
            return None

    def list_by_parent(self, parent_id: Optional[str]) -> List[GeoUnit]:
        with self._lock:
            return [u for u in self._store.values() if u.parent_id == parent_id]

    def list_by_level(self, level: ResolutionTier) -> List[GeoUnit]:
        with self._lock:
            return [u for u in self._store.values() if u.level == level]

    def search(self, query: str, limit: int = 50) -> List[GeoUnit]:
        with self._lock:
            q = query.strip().lower()
            if not q:
                return []
            matches = [u for u in self._store.values() if q in u.name.lower()]
            matches.sort(key=lambda u: (int(u.level), u.name))
            return matches[:limit]

    def update_geometry(
        self,
        unit_id: str,
        geometry: Optional[Dict[str, Any]],
        geometry_status: Union[str, GeometryStatus],
        preserve_existing: bool = True,
        geometry_source_record_id: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> bool:
        from shapely.geometry import shape

        from backend.arthlens.data.adapters.admin_boundaries import validate_boundary_geometry

        # 1. Validate explicit geometry_status enum
        if geometry_status is None:
            return False
        if isinstance(geometry_status, GeometryStatus):
            status_enum = geometry_status
        elif isinstance(geometry_status, str) and geometry_status in GeometryStatus._value2member_map_:
            status_enum = GeometryStatus(geometry_status)
        else:
            return False

        # 2. Status / Geometry consistency invariants
        # No geometry stored with GEOMETRY_MISSING
        if geometry is not None and status_enum == GeometryStatus.GEOMETRY_MISSING:
            return False
        # No missing geometry represented as verified/historical/simplified
        if geometry is None and status_enum in (
            GeometryStatus.GEOMETRY_VERIFIED,
            GeometryStatus.GEOMETRY_HISTORICAL,
            GeometryStatus.GEOMETRY_SIMPLIFIED,
        ):
            return False

        # 3. GeoJSON structural, coordinate, and topological checks
        if geometry is not None:
            is_valid, _ = validate_boundary_geometry(geometry)
            if not is_valid:
                return False
            try:
                s = shape(geometry)
                if s.geom_type not in ("Polygon", "MultiPolygon") or not s.is_valid:
                    return False
            except Exception:
                return False

        with self._lock:
            u = self._store.get(str(unit_id))
            if not u:
                return False

            existing_status = u.geometry_status.value if isinstance(u.geometry_status, GeometryStatus) else str(u.geometry_status)
            existing_rank = GEOMETRY_STATUS_RANK.get(existing_status, 0)
            candidate_rank = GEOMETRY_STATUS_RANK.get(status_enum.value, 0)

            # Preserve existing geometry invariants
            if preserve_existing and u.geometry is not None:
                if geometry is None:
                    return False
                if existing_rank > candidate_rank:
                    return False

            updated = GeoUnit(
                id=u.id,
                name=u.name,
                level=u.level,
                parent_id=u.parent_id,
                lgd_code=u.lgd_code,
                census_code=u.census_code,
                navigation_status=u.navigation_status,
                geometry_status=status_enum,
                analytical_status=u.analytical_status,
                geometry=geometry if geometry is not None else (None if status_enum == GeometryStatus.GEOMETRY_MISSING else u.geometry),
                geometry_source_record_id=geometry_source_record_id if geometry is not None else (None if status_enum == GeometryStatus.GEOMETRY_MISSING else u.geometry_source_record_id),
            )
            self._store[u.id] = updated
            return True

    def verify_geometry_validity(self, geometry: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not geometry:
            return False, "Geometry is empty or None."
        try:
            from shapely.geometry import shape
            from shapely.validation import explain_validity
            s = shape(geometry)
            if s.is_valid:
                return True, "Valid Geometry"
            return False, explain_validity(s)
        except Exception as e:
            return False, str(e)

    def get_coverage_summary(self) -> Dict[str, Any]:
        with self._lock:
            total_units = len(self._store)
            units_with_geom = sum(1 for u in self._store.values() if u.geometry is not None)
            status_counts: Dict[str, int] = {}
            for u in self._store.values():
                s = u.geometry_status.value if isinstance(u.geometry_status, GeometryStatus) else str(u.geometry_status)
                status_counts[s] = status_counts.get(s, 0) + 1
            tier_counts: Dict[str, Any] = {}
            for u in self._store.values():
                k = f"level_{int(u.level)}"
                if k not in tier_counts:
                    tier_counts[k] = {"total": 0, "with_geometry": 0}
                tier_counts[k]["total"] += 1
                if u.geometry is not None:
                    tier_counts[k]["with_geometry"] += 1
            return {
                "total_units": total_units,
                "units_with_geometry": units_with_geom,
                "units_missing_geometry": total_units - units_with_geom,
                "status_breakdown": status_counts,
                "geometry_status_breakdown": status_counts,
                "tier_breakdown": tier_counts,
                "ds09_source_records": 0,
            }

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
