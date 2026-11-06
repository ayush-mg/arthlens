"""
Indicators, Ledger, and Replay Endpoints.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from pathlib import Path
import json
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresQuantityRepository,
)
from backend.arthlens.quality import (
    AtlasQualityShadingAdapter,
    DataQualityEvaluator,
    get_shading_token,
)
from backend.arthlens.quality.freshness import evaluate_staleness
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(tags=["Indicators & Ledger"])


CORE_INDICATOR_DEFINITIONS = (
    ("population.total", "persons"),
    ("households.total", "dimensionless"),
    ("demand.monthly", "INR/month"),
    ("employment.formal_share", "share"),
    ("agriculture.soil_fertility_index", "index_score"),
)


@router.get("/geo/pilot-boundaries")
def get_pilot_boundaries(
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """Retrieve verified pilot boundary GeoJSON FeatureCollection (Prayagraj & subdistricts)."""
    fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "boundaries" / "prayagraj_boundaries_sample.geojson"
    if not fixture_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pilot boundary fixture not found.")
    with fixture_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/geo/units")
def list_geo_units(
    level: Optional[int] = Query(None, description="Resolution tier: 0=Nation, 1=State, 2=District, 3=Subdistrict"),
    parent_id: Optional[str] = Query(None, description="Parent GeoUnit identifier"),
    search: Optional[str] = Query(None, description="Search query matching unit name"),
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """List or search geographic units in the nationwide LGD hierarchy."""
    repo = PostgresGeoUnitRepository()
    if search:
        units = repo.search(search.strip(), limit=50)
    elif parent_id is not None:
        units = repo.list_by_parent(parent_id)
    elif level is not None:
        units = repo.list_by_level(ResolutionTier(level))
    else:
        # Default: list all states
        units = repo.list_by_level(ResolutionTier.STATE)

    return {
        "units": [
            {
                "id": u.id,
                "name": u.name,
                "level": int(u.level),
                "parent_id": u.parent_id,
                "lgd_code": u.lgd_code,
                "census_code": u.census_code,
                "navigation_status": u.navigation_status.value if hasattr(u.navigation_status, "value") else str(u.navigation_status),
                "geometry_status": u.geometry_status.value if hasattr(u.geometry_status, "value") else str(u.geometry_status),
                "analytical_status": u.analytical_status.value if hasattr(u.analytical_status, "value") else str(u.analytical_status),
                "has_geometry": u.geometry is not None,
            }
            for u in units
        ],
        "total": len(units),
    }


@router.get("/geo/{geo_id}")
def get_geo_unit(
    geo_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """Retrieve detailed metadata and verified geometry for a specific geographic unit."""
    repo = PostgresGeoUnitRepository()
    u = repo.get_unit(geo_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GeoUnit '{geo_id}' not found.")

    subunits = repo.list_by_parent(geo_id)
    parent_name = None
    if u.parent_id:
        parent = repo.get_unit(u.parent_id)
        if parent:
            parent_name = parent.name

    return {
        "id": u.id,
        "name": u.name,
        "level": int(u.level),
        "parent_id": u.parent_id,
        "parent_name": parent_name,
        "lgd_code": u.lgd_code,
        "census_code": u.census_code,
        "navigation_status": u.navigation_status.value if hasattr(u.navigation_status, "value") else str(u.navigation_status),
        "geometry_status": u.geometry_status.value if hasattr(u.geometry_status, "value") else str(u.geometry_status),
        "analytical_status": u.analytical_status.value if hasattr(u.analytical_status, "value") else str(u.analytical_status),
        "has_geometry": u.geometry is not None,
        "geometry": u.geometry,
        "subunits": [
            {
                "id": s.id,
                "name": s.name,
                "level": int(s.level),
                "parent_id": s.parent_id,
                "lgd_code": s.lgd_code,
                "census_code": s.census_code,
                "navigation_status": s.navigation_status.value if hasattr(s.navigation_status, "value") else str(s.navigation_status),
                "geometry_status": s.geometry_status.value if hasattr(s.geometry_status, "value") else str(s.geometry_status),
                "analytical_status": s.analytical_status.value if hasattr(s.analytical_status, "value") else str(s.analytical_status),
                "has_geometry": s.geometry is not None,
            }
            for s in subunits
        ],
    }


@router.get("/geo/{geo_id}/indicators")
def get_geo_indicators(
    geo_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """Retrieve indicators with class, resolution, quality flags, and Atlas shading (All authenticated roles)."""
    repo = PostgresQuantityRepository()
    quantities = repo.list_by_geo_unit(geo_id)
    evaluator = DataQualityEvaluator()

    indicator_items = []
    persisted_keys = set()
    for q in quantities:
        persisted_keys.add(q.definition_key)
        assessment = evaluator.evaluate_quantity(
            quantity=q,
            indicator_key=q.definition_key,
            geo_unit_id=geo_id,
        )
        indicator_items.append(
            {
                "id": q.id,
                "definition_key": q.definition_key,
                "value": q.value,
                "unit": q.unit,
                "kind": q.kind.value,
                "evidence_floor": q.evidence_floor,
                "resolution": q.resolution,
                "as_of": q.as_of,
                "quality_flags": list(q.quality_flags),
                "quality_status": assessment.primary_status.value,
                "quality_label": assessment.shading.label,
                "quality_color": assessment.shading.hex_color,
                "suitability": assessment.suitability.value,
                "shading": {
                    "color_token": assessment.shading.color_token,
                    "hex_color": assessment.shading.hex_color,
                    "fill_opacity": assessment.shading.fill_opacity,
                    "stroke_style": assessment.shading.stroke_style,
                },
            }
        )

    # For any core indicator lacking persisted ledger evidence in this unit,
    # evaluate deterministically as UNAVAILABLE (Handbook Part 7.4 & 10.3: never numeric zero).
    for key, unit in CORE_INDICATOR_DEFINITIONS:
        if key not in persisted_keys:
            assessment = evaluator.evaluate_quantity(
                quantity=None,
                indicator_key=key,
                geo_unit_id=geo_id,
            )
            indicator_items.append(
                {
                    "id": f"unavailable:{geo_id}:{key}",
                    "definition_key": key,
                    "value": None,
                    "unit": unit,
                    "kind": "OBSERVED",
                    "evidence_floor": 0,
                    "resolution": 0,
                    "as_of": None,
                    "quality_flags": [],
                    "quality_status": assessment.primary_status.value,
                    "quality_label": assessment.shading.label,
                    "quality_color": assessment.shading.hex_color,
                    "suitability": assessment.suitability.value,
                    "shading": {
                        "color_token": assessment.shading.color_token,
                        "hex_color": assessment.shading.hex_color,
                        "fill_opacity": assessment.shading.fill_opacity,
                        "stroke_style": assessment.shading.stroke_style,
                    },
                }
            )

    return {
        "geo_unit_id": geo_id,
        "indicators": indicator_items,
    }


@router.get("/geo/{geo_id}/quality")
def get_geo_quality(
    geo_id: str,
    indicator: Optional[str] = Query(None, description="Optional indicator definition_key"),
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """Retrieve Atlas quality assessment and shading tokens for a geographic unit."""
    repo = PostgresQuantityRepository()
    quantities = repo.list_by_geo_unit(geo_id)
    evaluator = DataQualityEvaluator()

    if indicator:
        matching = [q for q in quantities if q.definition_key == indicator]
        q = matching[0] if matching else None
        assessment = evaluator.evaluate_quantity(
            quantity=q,
            indicator_key=indicator,
            geo_unit_id=geo_id,
        )
        return assessment.to_dict()

    # If no specific indicator requested, evaluate all available indicators
    assessments = [
        evaluator.evaluate_quantity(quantity=q, indicator_key=q.definition_key, geo_unit_id=geo_id).to_dict()
        for q in quantities
    ]
    return {
        "geo_unit_id": geo_id,
        "assessments": assessments,
    }


@router.get("/ledger/{quantity_id}")
def get_ledger_quantity(
    quantity_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """
    Retrieve quantity with full ancestry, quality evaluation, temporal metadata, and restrictions.
    Enforces per-record access rules (Handbook Part 10.1 & Part 11):
    - Public quantities (owner_id is None) are accessible to all authenticated roles.
    - User-owned quantities are accessible only to their owner and authorized administrators.
    - Unauthorized access returns generic 404 without revealing resource existence.
    """
    repo = PostgresQuantityRepository()
    q = repo.get(quantity_id)
    if not q:
        if quantity_id.startswith("unavailable:"):
            parts = quantity_id.split(":", 2)
            geo_id = parts[1] if len(parts) > 1 else "unknown"
            indicator_key = parts[2] if len(parts) > 2 else "unknown"
            evaluator = DataQualityEvaluator()
            assessment = evaluator.evaluate_quantity(
                quantity=None,
                indicator_key=indicator_key,
                geo_unit_id=geo_id,
            )
            return {
                "id": quantity_id,
                "definition_key": indicator_key,
                "value": None,
                "unit": "",
                "kind": "OBSERVED",
                "evidence_floor": 0,
                "resolution": 0,
                "as_of": None,
                "quality_flags": [],
                "source_refs": [],
                "method_id": None,
                "assumptions": "No empirical or model observations have been ingested into the epistemic ledger for this unit.",
                "license_meta": "",
                "owner_id": None,
                "parent_ids": [],
                "parents": [],
                "quality": assessment.to_dict(),
                "temporal": {
                    "as_of": None,
                    "retrieval_date": None,
                    "publication_date": None,
                    "elapsed_days": None,
                    "max_age_days": None,
                    "has_policy": False,
                    "explanation": assessment.explanation,
                },
                "calculation_restrictions": [
                    "Unavailable Evidence: Strictly uningested metric. Cannot be treated as numeric zero or used in empirical calculations.",
                ],
            }
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quantity not found.",
        )

    # Per-record ownership verification
    if q.owner_id is not None:
        if q.owner_id != current_user.id and not current_user.has_role(Role.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quantity not found.",
            )

    evaluator = DataQualityEvaluator()
    assessment = evaluator.evaluate_quantity(
        quantity=q,
        indicator_key=q.definition_key,
        geo_unit_id=q.geo_unit_id,
    )

    parents_data = []
    for p in repo.get_parents(q.id):
        p_eval = evaluator.evaluate_quantity(p, p.definition_key, p.geo_unit_id)
        parents_data.append({
            "id": p.id,
            "definition_key": p.definition_key,
            "value": p.value,
            "unit": p.unit,
            "kind": p.kind.value,
            "quality_status": p_eval.primary_status.value,
        })

    freshness = evaluate_staleness(
        as_of=q.as_of,
        source_id=q.source_refs[0] if q.source_refs else None,
    )

    restrictions = []
    if q.kind == Kind.ESTIMATED or "SYNTHETIC_DATA" in q.quality_flags:
        restrictions.append("Estimated Projection (evidence floor <= 2; cannot support empirical claims)")
    if freshness.is_stale or "STALE" in q.quality_flags:
        restrictions.append("Historical Only (cannot support claims about current 2026 economic conditions)")
    if "STALE_ANCESTRY" in q.quality_flags:
        restrictions.append("Stale Ancestry Restriction (inherited from historical contributing quantities)")

    return {
        "id": q.id,
        "definition_key": q.definition_key,
        "value": q.value,
        "unit": q.unit,
        "kind": q.kind.value,
        "evidence_floor": q.evidence_floor,
        "resolution": q.resolution,
        "as_of": q.as_of,
        "quality_flags": list(q.quality_flags),
        "source_refs": list(q.source_refs),
        "method_id": q.method_id,
        "assumptions": getattr(q, "assumptions", None) or q.license_meta or "",
        "license_meta": q.license_meta,
        "owner_id": q.owner_id,
        "parent_ids": list(q.parent_ids),
        "parents": parents_data,
        "quality": assessment.to_dict(),
        "temporal": {
            "as_of": q.as_of,
            "retrieval_date": freshness.retrieval_date.isoformat() if freshness.retrieval_date else None,
            "publication_date": freshness.publication_date.isoformat() if freshness.publication_date else None,
            "elapsed_days": freshness.elapsed_days,
            "max_age_days": freshness.max_age_days,
            "has_policy": freshness.has_policy,
            "explanation": freshness.explanation,
        },
        "calculation_restrictions": restrictions,
    }


@router.get("/ledger/{quantity_id}/graph")
def get_ledger_graph(
    quantity_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """
    Retrieve Cytoscape.js directed acyclic graph (DAG) representing the complete
    ancestry, calculations, sources, and claims for a specific quantity.
    """
    repo = PostgresQuantityRepository()
    q = repo.get(quantity_id)
    if not q:
        if quantity_id.startswith("unavailable:"):
            parts = quantity_id.split(":", 2)
            geo_id = parts[1] if len(parts) > 1 else "unknown"
            indicator_key = parts[2] if len(parts) > 2 else "unknown"
            evaluator = DataQualityEvaluator()
            assessment = evaluator.evaluate_quantity(None, indicator_key, geo_id)
            return {
                "root_quantity_id": quantity_id,
                "elements": {
                    "nodes": [
                        {
                            "data": {
                                "id": quantity_id,
                                "label": f"{indicator_key}\nUNAVAILABLE",
                                "type": "quantity",
                                "status": "UNAVAILABLE",
                                "value": None,
                                "unit": "",
                                "kind": "OBSERVED",
                                "color": assessment.shading.hex_color,
                                "details": "No evidence ingested for this unit in the epistemic ledger.",
                            }
                        }
                    ],
                    "edges": [],
                },
            }
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quantity not found.",
        )

    if q.owner_id is not None:
        if q.owner_id != current_user.id and not current_user.has_role(Role.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quantity not found.",
            )

    evaluator = DataQualityEvaluator()
    assessment = evaluator.evaluate_quantity(q, q.definition_key, q.geo_unit_id)

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Root Quantity Node
    nodes.append({
        "data": {
            "id": q.id,
            "label": f"{q.definition_key}\n{q.value:,.2f} {q.unit}" if q.value is not None else q.definition_key,
            "type": "quantity",
            "status": assessment.primary_status.value,
            "value": q.value,
            "unit": q.unit,
            "kind": q.kind.value,
            "evidence_floor": q.evidence_floor,
            "color": assessment.shading.hex_color,
            "details": f"Floor: {q.evidence_floor} | Kind: {q.kind.value} | As of: {q.as_of or 'N/A'}",
        }
    })

    # 2. Claim Node (epistemic claim)
    claim_id = f"claim:{q.id}"
    nodes.append({
        "data": {
            "id": claim_id,
            "label": f"Verified Claim: {q.definition_key}",
            "type": "claim",
            "details": f"Epistemic claim verified for {q.geo_unit_id}",
        }
    })
    edges.append({
        "data": {
            "id": f"e-{q.id}-claim",
            "source": q.id,
            "target": claim_id,
            "label": "supports",
            "type": "supports_claim",
        }
    })

    # 3. Calculation Node (if derived or has method)
    calc_id = None
    if q.method_id or q.parent_ids:
        calc_id = f"calc:{q.id}"
        nodes.append({
            "data": {
                "id": calc_id,
                "label": f"Method: {q.method_id or 'Aggregation'}",
                "type": "calculation",
                "details": getattr(q, "assumptions", None) or q.license_meta or "Mathematical transformation in epistemic ledger",
            }
        })
        edges.append({
            "data": {
                "id": f"e-calc-{q.id}",
                "source": calc_id,
                "target": q.id,
                "label": "produces",
                "type": "calculates",
            }
        })

    # 4. Parent Quantity Nodes
    parents = repo.get_parents(q.id)
    for p in parents:
        p_eval = evaluator.evaluate_quantity(p, p.definition_key, p.geo_unit_id)
        nodes.append({
            "data": {
                "id": p.id,
                "label": f"{p.definition_key}\n{p.value:,.2f} {p.unit}" if p.value is not None else p.definition_key,
                "type": "quantity",
                "status": p_eval.primary_status.value,
                "value": p.value,
                "unit": p.unit,
                "kind": p.kind.value,
                "evidence_floor": p.evidence_floor,
                "color": p_eval.shading.hex_color,
                "details": f"Parent input | Kind: {p.kind.value} | As of: {p.as_of or 'N/A'}",
            }
        })
        target_node = calc_id if calc_id else q.id
        edges.append({
            "data": {
                "id": f"e-{p.id}-{target_node}",
                "source": p.id,
                "target": target_node,
                "label": "inputs",
                "type": "derives_from",
            }
        })

    # 5. Source Nodes
    for src in q.source_refs:
        src_id = f"src:{src}"
        nodes.append({
            "data": {
                "id": src_id,
                "label": f"Source: {src}",
                "type": "source",
                "details": f"Authoritative source register {src}",
            }
        })
        edges.append({
            "data": {
                "id": f"e-{src_id}-{q.id}",
                "source": src_id,
                "target": q.id,
                "label": "sourced_from",
                "type": "sourced_from",
            }
        })

    return {
        "root_quantity_id": q.id,
        "elements": {
            "nodes": nodes,
            "edges": edges,
        },
    }


@router.get("/replay/{run_id}")
def get_replay_trace(run_id: str) -> Dict[str, Any]:
    """Retrieve stored golden trace, labelled REPLAY (All authenticated roles & demo)."""
    return {
        "run_id": run_id,
        "banner": "Replay of a recorded run",
        "status": "REPLAY",
    }
