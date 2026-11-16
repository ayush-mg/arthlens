"""Persistence boundary for immutable business scenarios and seeded simulation runs."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from typing import Any, Mapping, Sequence

from sqlalchemy import select

from backend.arthlens.finance.scenarios import SCENARIO_MODEL_VERSION, run_monte_carlo, run_scenario, validate_assumptions
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import BusinessScenarioModel, BusinessScenarioVersionModel, BusinessSimulationRunModel


class ScenarioNotFoundError(LookupError):
    pass


class ScenarioReplayMismatchError(RuntimeError):
    pass


def _canonical_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scenario_dict(row: BusinessScenarioModel) -> dict[str, Any]:
    return {
        "id": str(row.id), "business_id": str(row.business_id), "name": row.name,
        "description": row.description, "current_version": row.current_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _version_dict(row: BusinessScenarioVersionModel) -> dict[str, Any]:
    return {
        "id": str(row.id), "scenario_id": str(row.scenario_id),
        "version_number": row.version_number, "assumptions": row.assumptions,
        "baseline_snapshot_hash": row.baseline_snapshot_hash,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class ScenarioService:
    def __init__(self) -> None:
        self._session_factory = get_session_factory()

    def create(self, business_id: uuid.UUID, user_id: uuid.UUID, name: str, description: str, assumptions: Mapping[str, Any]) -> dict[str, Any]:
        normalized = validate_assumptions(assumptions)
        digest = _canonical_hash(normalized)
        with self._session_factory() as session, session.begin():
            scenario = BusinessScenarioModel(
                business_id=business_id, created_by_user_id=user_id, name=name.strip(),
                description=description.strip(), current_version=1,
            )
            session.add(scenario)
            session.flush()
            version = BusinessScenarioVersionModel(
                scenario_id=scenario.id, version_number=1, assumptions=normalized,
                baseline_snapshot_hash=digest, created_by_user_id=user_id,
            )
            session.add(version)
            session.flush()
            return {**_scenario_dict(scenario), "latest_version": _version_dict(version), "analysis": run_scenario(normalized)}

    def list_scenarios(self, business_id: uuid.UUID) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            rows = session.scalars(select(BusinessScenarioModel).where(
                BusinessScenarioModel.business_id == business_id,
            ).order_by(BusinessScenarioModel.updated_at.desc(), BusinessScenarioModel.created_at.desc())).all()
            return [_scenario_dict(row) for row in rows]

    def delete(self, business_id: uuid.UUID, scenario_id: uuid.UUID) -> dict[str, Any]:
        with self._session_factory() as session, session.begin():
            scenario = session.scalar(select(BusinessScenarioModel).where(
                BusinessScenarioModel.id == scenario_id,
                BusinessScenarioModel.business_id == business_id,
            ))
            if scenario is None:
                raise ScenarioNotFoundError("Scenario was not found in this workspace.")
            name = scenario.name
            session.delete(scenario)
            return {"status": "deleted", "scenario_id": str(scenario_id), "name": name}

    def create_version(self, business_id: uuid.UUID, scenario_id: uuid.UUID, user_id: uuid.UUID, assumptions: Mapping[str, Any]) -> dict[str, Any]:
        normalized = validate_assumptions(assumptions)
        digest = _canonical_hash(normalized)
        with self._session_factory() as session, session.begin():
            scenario = session.scalar(select(BusinessScenarioModel).where(
                BusinessScenarioModel.id == scenario_id,
                BusinessScenarioModel.business_id == business_id,
            ).with_for_update())
            if scenario is None:
                raise ScenarioNotFoundError("Scenario was not found in this workspace.")
            next_version = scenario.current_version + 1
            version = BusinessScenarioVersionModel(
                scenario_id=scenario.id, version_number=next_version, assumptions=normalized,
                baseline_snapshot_hash=digest, created_by_user_id=user_id,
            )
            scenario.current_version = next_version
            session.add(version)
            session.flush()
            return {**_scenario_dict(scenario), "latest_version": _version_dict(version), "analysis": run_scenario(normalized)}

    def list_versions(self, business_id: uuid.UUID, scenario_id: uuid.UUID) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            exists = session.scalar(select(BusinessScenarioModel.id).where(
                BusinessScenarioModel.id == scenario_id, BusinessScenarioModel.business_id == business_id,
            ))
            if exists is None:
                raise ScenarioNotFoundError("Scenario was not found in this workspace.")
            rows = session.scalars(select(BusinessScenarioVersionModel).join(
                BusinessScenarioModel, BusinessScenarioModel.id == BusinessScenarioVersionModel.scenario_id,
            ).where(
                BusinessScenarioModel.business_id == business_id,
                BusinessScenarioVersionModel.scenario_id == scenario_id,
            ).order_by(BusinessScenarioVersionModel.version_number.desc())).all()
            return [{**_version_dict(row), "analysis": run_scenario(row.assumptions)} for row in rows]

    def compare_versions(self, business_id: uuid.UUID, version_ids: Sequence[uuid.UUID]) -> dict[str, Any]:
        if len(version_ids) < 2 or len(version_ids) > 5:
            raise ValueError("Compare between 2 and 5 scenario versions.")
        with self._session_factory() as session:
            rows = session.scalars(select(BusinessScenarioVersionModel).join(
                BusinessScenarioModel, BusinessScenarioModel.id == BusinessScenarioVersionModel.scenario_id,
            ).where(
                BusinessScenarioModel.business_id == business_id,
                BusinessScenarioVersionModel.id.in_(version_ids),
            )).all()
            if len({row.id for row in rows}) != len(set(version_ids)):
                raise ScenarioNotFoundError("One or more scenario versions were not found in this workspace.")
            ordered = {row.id: row for row in rows}
            comparisons = []
            for version_id in version_ids:
                row = ordered[version_id]
                analysis = run_scenario(row.assumptions)
                scenario = session.get(BusinessScenarioModel, row.scenario_id)
                comparisons.append({
                    "scenario_id": str(row.scenario_id), "scenario_name": scenario.name if scenario else "",
                    "version_id": str(row.id), "version_number": row.version_number,
                    "baseline_snapshot_hash": row.baseline_snapshot_hash,
                    "cases": {case: result["summary"] for case, result in analysis["cases"].items()},
                })
            return {"versions": comparisons}

    def run_monte_carlo(self, business_id: uuid.UUID, scenario_id: uuid.UUID, user_id: uuid.UUID, iterations: int, random_seed: int | None, distribution_config: Mapping[str, Any] | None = None, distributions: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._session_factory() as session:
            version = session.scalar(select(BusinessScenarioVersionModel).join(
                BusinessScenarioModel, BusinessScenarioModel.id == BusinessScenarioVersionModel.scenario_id,
            ).where(
                BusinessScenarioModel.business_id == business_id,
                BusinessScenarioModel.id == scenario_id,
                BusinessScenarioModel.current_version == BusinessScenarioVersionModel.version_number,
            ))
            if version is None:
                raise ScenarioNotFoundError("Scenario was not found in this workspace.")
            assumptions = dict(version.assumptions)
            seed = secrets.randbits(64) if random_seed is None else random_seed
            active_dist = distributions if distributions is not None else distribution_config
            dists = active_dist if active_dist is not None else assumptions.get("distributions", {})
            result = run_monte_carlo(assumptions, dists, iterations, seed)
            row = BusinessSimulationRunModel(
                business_id=business_id, scenario_version_id=version.id, random_seed=seed,
                iterations=iterations, distribution_config=result["distributions"],
                baseline_snapshot_hash=version.baseline_snapshot_hash,
                model_version=SCENARIO_MODEL_VERSION, result=result, created_by_user_id=user_id,
            )
            session.add(row)
            session.commit()
            return {
                "id": str(row.id), "scenario_version_id": str(version.id),
                "baseline_snapshot_hash": row.baseline_snapshot_hash,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "result": result, **result,
            }

    def replay(self, business_id: uuid.UUID, run_id: uuid.UUID) -> dict[str, Any]:
        with self._session_factory() as session:
            run = session.scalar(select(BusinessSimulationRunModel).where(
                BusinessSimulationRunModel.id == run_id,
                BusinessSimulationRunModel.business_id == business_id,
            ))
            if run is None:
                raise ScenarioNotFoundError("Simulation run was not found in this workspace.")
            version = session.get(BusinessScenarioVersionModel, run.scenario_version_id)
            if version is None or version.baseline_snapshot_hash != run.baseline_snapshot_hash:
                raise ScenarioReplayMismatchError("Stored scenario snapshot does not match the simulation run.")
            replayed = run_monte_carlo(version.assumptions, run.distribution_config, run.iterations, int(run.random_seed))
            if replayed != run.result:
                raise ScenarioReplayMismatchError("Seeded replay did not reproduce the stored simulation output.")
            return {
                "run_id": str(run.id), "scenario_id": str(version.scenario_id),
                "scenario_version_id": str(version.id), "replayed": True,
                "random_seed": int(run.random_seed), "result": replayed,
            }

    def list_runs(self, business_id: uuid.UUID, scenario_id: uuid.UUID) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            scenario_exists = session.scalar(select(BusinessScenarioModel.id).where(
                BusinessScenarioModel.id == scenario_id, BusinessScenarioModel.business_id == business_id,
            ))
            if scenario_exists is None:
                raise ScenarioNotFoundError("Scenario was not found in this workspace.")
            rows = session.scalars(select(BusinessSimulationRunModel).join(
                BusinessScenarioVersionModel,
                BusinessScenarioVersionModel.id == BusinessSimulationRunModel.scenario_version_id,
            ).where(
                BusinessSimulationRunModel.business_id == business_id,
                BusinessScenarioVersionModel.scenario_id == scenario_id,
            ).order_by(BusinessSimulationRunModel.created_at.desc())).all()
            return [{
                "id": str(row.id), "scenario_id": str(scenario_id),
                "scenario_version_id": str(row.scenario_version_id),
                "random_seed": int(row.random_seed), "iterations": row.iterations,
                "distribution_config": row.distribution_config,
                "baseline_snapshot_hash": row.baseline_snapshot_hash,
                "model_version": row.model_version, "result": row.result,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            } for row in rows]


_scenario_service: ScenarioService | None = None


def get_scenario_service() -> ScenarioService:
    global _scenario_service
    if _scenario_service is None:
        _scenario_service = ScenarioService()
    return _scenario_service
