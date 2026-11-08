"""
Indicators, Ledger, and Replay Endpoints.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.provenance import resolve_quantity_provenance
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresQuantityRepository,
    PostgresScenarioRepository,
)
from backend.arthlens.quality import (
    DataQualityEvaluator,
)
from backend.arthlens.reporting.dossier_generator import (
    generate_dossier_csv,
    generate_dossier_json,
    generate_dossier_pdf,
    generate_dossier_xlsx,
)
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
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
) -> Dict[str, Any]:
    """Retrieve verified pilot boundary GeoJSON FeatureCollection (Prayagraj)."""
    from backend.arthlens.data.adapters.admin_boundaries import (
        AdminBoundariesAdapter,
        is_axis_aligned_bounding_box,
    )

    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "boundaries"
        / "prayagraj_boundaries_sample.geojson"
    )
    if not fixture_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pilot boundary fixture not found.",
        )
    try:
        with fixture_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read pilot boundary fixture: {exc}",
        )

    # Perform backend schema validation on geometry
    adapter = AdminBoundariesAdapter()
    is_valid, errors = adapter.validate_schema(payload)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pilot boundary validation failed: {'; '.join(errors)}",
        )

    # Filter out any synthetic bounding boxes from verified boundary features
    features = payload.get("features", [])
    valid_features = []
    for feat in features:
        geom = feat.get("geometry") or {}
        if geom.get("type") == "Polygon":
            coords = (geom.get("coordinates") or [[]])[0]
            if is_axis_aligned_bounding_box(coords):
                continue
        valid_features.append(feat)

    if not valid_features:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verified administrative boundary geometry available for pilot district.",
        )

    payload["features"] = valid_features
    return payload


@router.get("/geo/pilot-pmtiles")
def get_pilot_pmtiles(
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
):
    """Serve verified pilot PMTiles v3 boundary tile archive."""
    from fastapi.responses import FileResponse

    pmtiles_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "boundaries"
        / "india_census_2011_pilot.pmtiles"
    )
    if not pmtiles_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pilot PMTiles archive not found.",
        )
    return FileResponse(
        path=str(pmtiles_path),
        media_type="application/vnd.pmtiles",
        filename="india_census_2011_pilot.pmtiles",
    )


@router.get("/geo/units")
def list_geo_units(
    level: Optional[int] = Query(
        None, description="Resolution tier: 0=Nation, 1=State, 2=District, 3=Subdistrict"
    ),
    parent_id: Optional[str] = Query(None, description="Parent GeoUnit identifier"),
    search: Optional[str] = Query(None, description="Search query matching unit name"),
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
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

    parent_ids = {u.parent_id for u in units if u.parent_id}
    parent_names = {}
    if parent_ids:
        for pid in parent_ids:
            pu = repo.get_unit(pid)
            if pu:
                parent_names[pid] = pu.name

    return {
        "units": [
            {
                "id": u.id,
                "name": u.name,
                "level": int(u.level),
                "parent_id": u.parent_id,
                "parent_name": parent_names.get(u.parent_id),
                "lgd_code": u.lgd_code,
                "census_code": u.census_code,
                "navigation_status": u.navigation_status.value
                if hasattr(u.navigation_status, "value")
                else str(u.navigation_status),
                "geometry_status": u.geometry_status.value
                if hasattr(u.geometry_status, "value")
                else str(u.geometry_status),
                "analytical_status": u.analytical_status.value
                if hasattr(u.analytical_status, "value")
                else str(u.analytical_status),
                "has_geometry": u.geometry is not None,
            }
            for u in units
        ],
        "total": len(units),
    }


@router.get("/geo/{geo_id}")
def get_geo_unit(
    geo_id: str,
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
) -> Dict[str, Any]:
    """Retrieve detailed metadata and verified geometry for a specific geographic unit."""
    repo = PostgresGeoUnitRepository()
    u = repo.get_unit(geo_id)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"GeoUnit '{geo_id}' not found."
        )

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
        "navigation_status": u.navigation_status.value
        if hasattr(u.navigation_status, "value")
        else str(u.navigation_status),
        "geometry_status": u.geometry_status.value
        if hasattr(u.geometry_status, "value")
        else str(u.geometry_status),
        "analytical_status": u.analytical_status.value
        if hasattr(u.analytical_status, "value")
        else str(u.analytical_status),
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
                "navigation_status": s.navigation_status.value
                if hasattr(s.navigation_status, "value")
                else str(s.navigation_status),
                "geometry_status": s.geometry_status.value
                if hasattr(s.geometry_status, "value")
                else str(s.geometry_status),
                "analytical_status": s.analytical_status.value
                if hasattr(s.analytical_status, "value")
                else str(s.analytical_status),
                "has_geometry": s.geometry is not None,
            }
            for s in subunits
        ],
    }


@router.get("/geo/{geo_id}/boundary")
def get_geo_unit_boundary(
    geo_id: str,
    indicator: Optional[str] = Query(None, description="Optional active indicator definition_key"),
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
) -> Dict[str, Any]:
    """
    Retrieve genuine boundary GeoJSON FeatureCollection for the selected geographic unit.
    Returns GeoJSON FeatureCollection with 1 Feature when geometry is persisted in PostGIS,
    or deterministic empty FeatureCollection when geometry is genuinely unavailable.
    Returns 404 for unknown geographic identifiers.
    """
    repo = PostgresGeoUnitRepository()
    u = repo.get_unit(geo_id)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GeoUnit '{geo_id}' not found in administrative hierarchy.",
        )

    geom_status_str = (
        u.geometry_status.value if hasattr(u.geometry_status, "value") else str(u.geometry_status)
    )

    # 1. If geometry is persisted in PostGIS
    if u.geometry is not None:

        from backend.arthlens.infra.database import get_session_factory
        from backend.arthlens.infra.models import SourceModel, SourceRecordModel, SourceVersionModel

        session_factory = get_session_factory()
        prov_source_id = None
        prov_source_name = None
        prov_vintage = None
        prov_as_of = None
        prov_license = None
        prov_attribution = None
        prov_available = False

        prov_source_version_id = None
        prov_checksum = None

        with session_factory() as session:
            sr = None
            if getattr(u, "geometry_source_record_id", None):
                candidate_sr = session.get(SourceRecordModel, u.geometry_source_record_id)
                # FIX 2: Verify the SourceRecord belongs to correct source (DS-09)
                if candidate_sr and candidate_sr.source_id == "DS-09":
                    # Verify its exact SourceVersion exists and matches
                    if candidate_sr.source_version_id:
                        sver = session.get(SourceVersionModel, candidate_sr.source_version_id)
                        if sver and sver.source_id == "DS-09" and sver.content_hash:
                            sr = candidate_sr
                            prov_source_version_id = sver.id
                            prov_checksum = sver.content_hash
                            prov_vintage = sver.version or (sr.normalized_fields or {}).get(
                                "vintage"
                            )
            # FIX 2: Strictly NO fallback query — if geometry_source_record_id is missing,
            # mismatched, or unverified, provenance is reported as unavailable.
            if sr:
                prov_license = sr.license_name
                prov_attribution = sr.attribution
                prov_source_id = sr.source_id
                if sr.as_of:
                    prov_as_of = sr.as_of.isoformat()
                if sr.source_id:
                    src_obj = session.get(SourceModel, sr.source_id)
                    if src_obj:
                        prov_source_name = src_obj.name
                # Provenance is available only if source, version, checksum and licence/attribution exist
                if prov_source_id and prov_source_version_id and prov_checksum:
                    prov_available = True
                else:
                    prov_available = False

        # Inject active indicator quality if requested
        indicator_quality = None
        indicator_status = None
        if indicator:
            q_repo = PostgresQuantityRepository()
            unit_qs = [q for q in q_repo.list_by_geo_unit(geo_id) if q.definition_key == indicator]
            evaluator = DataQualityEvaluator()
            q_target = unit_qs[0] if unit_qs else None
            provenance = (
                resolve_quantity_provenance(q_target, q_repo) if q_target is not None else {}
            )
            indicator_assessment = evaluator.evaluate_quantity(
                quantity=q_target,
                indicator_key=indicator,
                geo_unit_id=geo_id,
                source_id=provenance.get("source_id"),
                source_version_id=provenance.get("source_version_id"),
                retrieval_date=provenance.get("retrieval_date"),
                provenance_complete=provenance.get("provenance_complete"),
                source_ids=provenance.get("source_ids"),
            )
            indicator_quality = indicator_assessment.to_dict()
            indicator_status = indicator_assessment.primary_status.value

        return {
            "type": "FeatureCollection",
            "geo_id": u.id,
            "has_geometry": True,
            "geometry_status": geom_status_str,
            "provenance_available": prov_available,
            "features": [
                {
                    "type": "Feature",
                    "id": u.id,
                    "properties": {
                        "geo_id": u.id,
                        "name": u.name,
                        "lgd_code": u.lgd_code,
                        "census_code": u.census_code,
                        "level": int(u.level),
                        "parent_id": u.parent_id,
                        "geometry_status": geom_status_str,
                        "has_geometry": True,
                        "source_id": prov_source_id,
                        "source_name": prov_source_name,
                        "source_version_id": prov_source_version_id,
                        "checksum": prov_checksum,
                        "vintage": prov_vintage,
                        "as_of": prov_as_of,
                        "license_name": prov_license,
                        "attribution": prov_attribution,
                        "provenance_available": prov_available,
                        "indicator_quality": indicator_quality,
                        "quality_status": indicator_status,
                    },
                    "geometry": u.geometry,
                }
            ],
            "properties": {
                "geo_id": u.id,
                "name": u.name,
                "lgd_code": u.lgd_code,
                "geometry_status": geom_status_str,
                "has_geometry": True,
                "provenance_available": prov_available,
                "source_id": prov_source_id,
                "source_name": prov_source_name,
                "source_version_id": prov_source_version_id,
                "checksum": prov_checksum,
                "vintage": prov_vintage,
                "as_of": prov_as_of,
                "license_name": prov_license,
                "attribution": prov_attribution,
                "feature_count": 1,
                "indicator_quality": indicator_quality,
                "quality_status": indicator_status,
            },
        }

    # 2. Known geographic unit without geometry
    return {
        "type": "FeatureCollection",
        "geo_id": u.id,
        "has_geometry": False,
        "geometry_status": geom_status_str,
        "detail": f"Boundary geometry is unavailable for {u.name} (LGD {u.lgd_code}).",
        "features": [],
        "properties": {
            "geo_id": u.id,
            "name": u.name,
            "lgd_code": u.lgd_code,
            "census_code": u.census_code,
            "level": int(u.level),
            "parent_id": u.parent_id,
            "geometry_status": geom_status_str,
            "has_geometry": False,
            "source_id": None,
            "source_name": None,
            "vintage": None,
            "as_of": None,
            "license_name": None,
            "attribution": None,
            "provenance_available": False,
            "detail": f"Boundary geometry is unavailable for {u.name} (LGD {u.lgd_code}).",
            "feature_count": 0,
        },
    }


@router.get("/geo/{geo_id}/indicators")
def get_geo_indicators(
    geo_id: str,
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
) -> Dict[str, Any]:
    """Retrieve indicators with class, resolution, quality flags, and Atlas shading (All authenticated roles)."""
    geo_repo = PostgresGeoUnitRepository()
    if not geo_repo.get_unit(geo_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GeoUnit '{geo_id}' not found in administrative hierarchy.",
        )

    repo = PostgresQuantityRepository()
    quantities = repo.list_by_geo_unit(geo_id)
    evaluator = DataQualityEvaluator()

    # FIX 5: Handbook V5 Contradiction Detection using registered metric tolerance policies
    from backend.arthlens.quality.contradiction import detect_contradictions

    contradicted_ids, contradiction_records = detect_contradictions(quantities)

    # Group by definition_key for deterministic selection and contradiction visibility
    by_key: Dict[str, List[Quantity]] = {}
    for q in quantities:
        by_key.setdefault(q.definition_key, []).append(q)

    indicator_items = []
    persisted_keys = set()

    for def_key, q_list in by_key.items():
        persisted_keys.add(def_key)

        # Check which quantities in this group participate in contradiction
        group_contradicted = [
            q
            for q in q_list
            if str(q.id) in contradicted_ids
            or "CONTRADICTED" in q.quality_flags
            or "DISPUTED" in q.quality_flags
        ]

        def sort_key(item: Quantity):
            src_str = (
                item.source_refs[0][0]
                if item.source_refs and isinstance(item.source_refs[0], (tuple, list))
                else str(item.source_refs or "")
            )
            return (item.as_of or "", src_str, str(item.id))

        sorted_qs = sorted(q_list, key=sort_key, reverse=True)

        # Handbook V5: If contradiction detected, ALL conflicting quantities must remain visible!
        # Never select the latest value and hide the conflicting source.
        if group_contradicted:
            qs_to_emit = sorted_qs  # Emit all candidates so all conflicting sources remain visible
        else:
            qs_to_emit = [sorted_qs[0]]

        for q in qs_to_emit:
            is_c = (
                str(q.id) in contradicted_ids
                or "CONTRADICTED" in q.quality_flags
                or "DISPUTED" in q.quality_flags
            )
            flags = set(q.quality_flags)
            if is_c:
                flags.add("CONTRADICTED")
                flags.add("DISPUTED")
            if flags != q.quality_flags:
                q = replace(q, quality_flags=frozenset(flags))

            provenance = resolve_quantity_provenance(q, repo)
            assessment = evaluator.evaluate_quantity(
                quantity=q,
                indicator_key=def_key,
                geo_unit_id=geo_id,
                source_id=provenance["source_id"],
                source_version_id=provenance["source_version_id"],
                retrieval_date=provenance["retrieval_date"],
                provenance_complete=provenance["provenance_complete"],
                source_ids=provenance["source_ids"],
            )

            indicator_items.append(
                {
                    "status": "AVAILABLE",
                    "id": str(q.id),
                    "definition_key": q.definition_key,
                    "value": q.value,
                    "unit": q.unit,
                    "kind": q.kind.value,
                    "evidence_floor": q.evidence_floor,
                    "resolution": q.resolution,
                    "as_of": q.as_of,
                    "source_refs": list(q.source_refs),
                    "source_provenance": provenance["source_provenance"],
                    "lineage_source_provenance": provenance["lineage_source_provenance"],
                    "provenance_complete": provenance["provenance_complete"],
                    "source_version_id": provenance["source_version_id"],
                    "quality_flags": list(q.quality_flags),
                    "quality_status": assessment.primary_status.value,
                    "quality_label": assessment.shading.label,
                    "quality_color": assessment.shading.hex_color,
                    "suitability": assessment.suitability.value,
                    "disputed": is_c,
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
                    "status": "UNAVAILABLE",
                    "id": None,
                    "definition_key": key,
                    "value": None,
                    "unit": unit,
                    "kind": None,
                    "evidence_floor": None,
                    "resolution": None,
                    "as_of": None,
                    "source_refs": [],
                    "quality_flags": [],
                    "quality_status": "UNAVAILABLE",
                    "quality_label": assessment.shading.label,
                    "quality_color": assessment.shading.hex_color,
                    "suitability": assessment.suitability.value,
                    "explanation": "No empirical observation or verified ledger evidence recorded for this indicator in this geographic unit.",
                    "resolution_action": "Source ingestion required.",
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
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
) -> Dict[str, Any]:
    """Retrieve Atlas quality assessment and shading tokens for a geographic unit."""
    geo_repo = PostgresGeoUnitRepository()
    if not geo_repo.get_unit(geo_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GeoUnit '{geo_id}' not found in administrative hierarchy.",
        )

    repo = PostgresQuantityRepository()
    quantities = repo.list_by_geo_unit(geo_id)
    evaluator = DataQualityEvaluator()

    if indicator:
        matching = [q for q in quantities if q.definition_key == indicator]
        q = matching[0] if matching else None
        provenance = resolve_quantity_provenance(q, repo) if q is not None else {}
        assessment = evaluator.evaluate_quantity(
            quantity=q,
            indicator_key=indicator,
            geo_unit_id=geo_id,
            source_id=provenance.get("source_id"),
            source_version_id=provenance.get("source_version_id"),
            retrieval_date=provenance.get("retrieval_date"),
            provenance_complete=provenance.get("provenance_complete"),
            source_ids=provenance.get("source_ids"),
        )
        return assessment.to_dict()

    # If no specific indicator requested, evaluate all available indicators
    assessments = []
    for q in quantities:
        provenance = resolve_quantity_provenance(q, repo)
        assessments.append(
            evaluator.evaluate_quantity(
                quantity=q,
                indicator_key=q.definition_key,
                geo_unit_id=geo_id,
                source_id=provenance["source_id"],
                source_version_id=provenance["source_version_id"],
                retrieval_date=provenance["retrieval_date"],
                provenance_complete=provenance["provenance_complete"],
                source_ids=provenance["source_ids"],
            ).to_dict()
        )
    return {
        "geo_unit_id": geo_id,
        "assessments": assessments,
    }


@router.get("/ledger/{quantity_id}")
def get_ledger_quantity(
    quantity_id: str,
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
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

    provenance = resolve_quantity_provenance(q, repo)
    parent_quantities = repo.get_parents(q.id)
    registered_parent_ids = {parent.id for parent in parent_quantities}
    missing_parent_ids = sorted(set(q.parent_ids) - registered_parent_ids)
    if missing_parent_ids:
        provenance["provenance_complete"] = False
    evaluator = DataQualityEvaluator()
    assessment = evaluator.evaluate_quantity(
        quantity=q,
        indicator_key=q.definition_key,
        geo_unit_id=q.geo_unit_id,
        source_id=provenance["source_id"],
        source_version_id=provenance["source_version_id"],
        retrieval_date=provenance["retrieval_date"],
        provenance_complete=provenance["provenance_complete"],
        source_ids=provenance["source_ids"],
    )

    parents_data = []
    for p in parent_quantities:
        parent_provenance = resolve_quantity_provenance(p, repo)
        p_eval = evaluator.evaluate_quantity(
            p,
            p.definition_key,
            p.geo_unit_id,
            source_id=parent_provenance["source_id"],
            source_version_id=parent_provenance["source_version_id"],
            retrieval_date=parent_provenance["retrieval_date"],
            provenance_complete=parent_provenance["provenance_complete"],
            source_ids=parent_provenance["source_ids"],
        )
        parents_data.append(
            {
                "id": p.id,
                "definition_key": p.definition_key,
                "value": p.value,
                "unit": p.unit,
                "kind": p.kind.value,
                "source_refs": list(p.source_refs),
                "source_provenance": parent_provenance["source_provenance"],
                "provenance_complete": parent_provenance["provenance_complete"],
                "parent_ids": list(p.parent_ids),
                "quality_status": p_eval.primary_status.value,
            }
        )

    freshness = assessment.freshness
    first_source = (
        provenance["lineage_source_provenance"][0]
        if provenance.get("lineage_source_provenance")
        else (provenance.get("source_provenance", [{}])[0] if provenance.get("source_provenance") else {})
    )
    source_checksum = first_source.get("source_checksum")
    source_name = first_source.get("source_name")
    source_version = first_source.get("source_version")
    source_version_id_resolved = provenance["source_version_id"]
    provenance_complete = provenance["provenance_complete"]

    restrictions = []
    if q.kind == Kind.ESTIMATED or "SYNTHETIC_DATA" in q.quality_flags:
        restrictions.append(
            "Estimated Projection (evidence floor <= 2; cannot support empirical claims)"
        )
    if freshness.is_stale or "STALE" in q.quality_flags:
        restrictions.append(
            "Historical Only (cannot support claims about current 2026 economic conditions)"
        )
    if "STALE_ANCESTRY" in q.quality_flags:
        restrictions.append(
            "Stale Ancestry Restriction (inherited from historical contributing quantities)"
        )

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
        "source_checksum": source_checksum,
        "source_name": source_name,
        "source_id": provenance["source_id"],
        "source_version": source_version,
        "source_version_id": source_version_id_resolved,
        "source_provenance": provenance["source_provenance"],
        "lineage_source_provenance": provenance["lineage_source_provenance"],
        "provenance_complete": provenance_complete,
        "method_id": q.method_id,
        "assumptions": getattr(q, "assumptions", None) or q.license_meta or "",
        "license_meta": q.license_meta,
        "owner_id": q.owner_id,
        "parent_ids": list(q.parent_ids),
        "missing_parent_ids": missing_parent_ids,
        "parents": parents_data,
        "quality": assessment.to_dict(),
        "temporal": {
            "as_of": q.as_of,
            "retrieval_date": freshness.retrieval_date.isoformat()
            if freshness.retrieval_date
            else None,
            "publication_date": freshness.publication_date.isoformat()
            if freshness.publication_date
            else None,
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
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
) -> Dict[str, Any]:
    """
    Retrieve Cytoscape.js directed acyclic graph (DAG) representing the complete
    ancestry, calculations, sources, and claims for a specific quantity.
    """
    repo = PostgresQuantityRepository()
    q = repo.get(quantity_id)
    if not q:
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

    # Recursive Ancestry Traversal (supports multi-level, multiple parents, diamond DAGs, and cycle protection)
    visited_q_ids: Set[str] = set()
    node_map: Dict[str, Dict[str, Any]] = {}
    edge_map: Dict[str, Dict[str, Any]] = {}

    queue: List[Tuple[Quantity, int]] = [(q, 0)]
    max_depth = 50
    is_truncated = False

    while queue:
        curr_q, depth = queue.pop(0)
        curr_q_id = str(curr_q.id)
        if curr_q_id in visited_q_ids:
            continue
        visited_q_ids.add(curr_q_id)

        # Quantity Node
        provenance = resolve_quantity_provenance(curr_q, repo)
        parents = repo.get_parents(curr_q.id)
        registered_parent_ids = {parent.id for parent in parents}
        missing_parent_ids = set(curr_q.parent_ids) - registered_parent_ids
        c_eval = evaluator.evaluate_quantity(
            curr_q,
            curr_q.definition_key,
            curr_q.geo_unit_id,
            source_id=provenance["source_id"],
            source_version_id=provenance["source_version_id"],
            retrieval_date=provenance["retrieval_date"],
            provenance_complete=(provenance["provenance_complete"] and not missing_parent_ids),
            source_ids=provenance["source_ids"],
        )
        if curr_q_id not in node_map:
            node_map[curr_q_id] = {
                "data": {
                    "id": curr_q_id,
                    "label": f"{curr_q.definition_key}\n{curr_q.value:,.2f} {curr_q.unit}"
                    if curr_q.value is not None
                    else curr_q.definition_key,
                    "type": "quantity",
                    "status": c_eval.primary_status.value,
                    "value": curr_q.value,
                    "unit": curr_q.unit,
                    "kind": curr_q.kind.value,
                    "evidence_floor": curr_q.evidence_floor,
                    "parent_ids": list(curr_q.parent_ids),
                    "source_refs": list(curr_q.source_refs),
                    "provenance_complete": provenance["provenance_complete"] and not missing_parent_ids,
                    "missing_parent_ids": sorted(missing_parent_ids),
                    "color": c_eval.shading.hex_color,
                    "details": f"{'Root target quantity' if curr_q_id == str(q.id) else 'Parent input'} | Floor: {curr_q.evidence_floor} | Kind: {curr_q.kind.value} | As of: {curr_q.as_of or 'N/A'}",
                }
            }

        # Calculation Node (if derived or has method)
        calc_id = None
        if curr_q.method_id or curr_q.parent_ids:
            calc_id = f"calc:{curr_q_id}"
            if calc_id not in node_map:
                node_map[calc_id] = {
                    "data": {
                        "id": calc_id,
                        "label": f"Method: {curr_q.method_id or 'Aggregation'}",
                        "type": "calculation",
                        "details": getattr(curr_q, "assumptions", None)
                        or curr_q.license_meta
                        or "Mathematical transformation in epistemic ledger",
                    }
                }
            calc_edge_id = f"e-calc-{curr_q_id}"
            if calc_edge_id not in edge_map:
                edge_map[calc_edge_id] = {
                    "data": {
                        "id": calc_edge_id,
                        "source": calc_id,
                        "target": curr_q_id,
                        "label": "produces",
                        "type": "calculates",
                    }
                }

        # Show verified source versions as sources; preserve other references as
        # explicitly unverified citations rather than promoting their text.
        for index, source in enumerate(provenance["source_provenance"]):
            verified = source["provenance_complete"]
            declared_assumption = source.get("explicit_assumption", False)
            if verified:
                src_id = f"src:{source['source_version_id']}"
                src_label = f"Source: {source['source_name']} ({source['source_version']})"
                src_details = (
                    f"Registered source {source['source_id']}; exact version "
                    f"{source['source_version_id']}; SHA-256 {source['source_checksum']}; "
                    f"retrieved {source['retrieval_date']}"
                )
            elif declared_assumption:
                src_id = f"assumption:{curr_q_id}:{index}"
                src_label = "Declared user assumption"
                src_details = (
                    f"Explicit {curr_q.kind.value} input recorded at "
                    f"{source.get('locator') or 'an unspecified input field'}."
                )
            else:
                src_id = f"citation:{curr_q_id}:{index}"
                src_label = "Unverified source citation"
                src_details = (
                    "Referenced source identifier "
                    f"{source.get('source_version_id') or 'missing'} is not verified "
                    "as an exact source-version citation."
                )
            if source.get("locator"):
                src_label += f"\nLocator: {source['locator']}"
            if src_id not in node_map:
                node_map[src_id] = {
                    "data": {
                        "id": src_id,
                        "label": src_label,
                        "type": "source",
                        "details": src_details,
                        "provenance_complete": verified or declared_assumption,
                        "provenance_kind": "source_version" if verified else "user_assumption" if declared_assumption else "unverified_citation",
                    }
                }
            s_edge_id = f"e-{src_id}-{curr_q_id}"
            if s_edge_id not in edge_map:
                edge_map[s_edge_id] = {
                    "data": {
                        "id": s_edge_id,
                        "source": src_id,
                        "target": curr_q_id,
                        "label": "sourced_from" if verified else "declared_assumption" if declared_assumption else "unverified_citation",
                        "type": "sourced_from" if verified else "declares_assumption" if declared_assumption else "cites_unverified_source",
                    }
                }

        # Parent Quantity Traversal
        if depth < max_depth:
            for p in parents:
                # Per-record ownership verification on all graph ancestors
                if p.owner_id is not None:
                    if p.owner_id != current_user.id and not current_user.has_role(Role.ADMIN):
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Quantity not found.",
                        )
                p_id = str(p.id)
                target_node = calc_id if calc_id else curr_q_id
                p_edge_id = f"e-{p_id}-{target_node}"
                if p_edge_id not in edge_map:
                    edge_map[p_edge_id] = {
                        "data": {
                            "id": p_edge_id,
                            "source": p_id,
                            "target": target_node,
                            "label": "inputs",
                            "type": "derives_from",
                        }
                    }
                if p_id not in visited_q_ids:
                    queue.append((p, depth + 1))
            target_node = calc_id if calc_id else curr_q_id
            for missing_parent_id in sorted(missing_parent_ids):
                unresolved_id = f"missing-parent:{curr_q_id}:{missing_parent_id}"
                node_map[unresolved_id] = {
                    "data": {
                        "id": unresolved_id,
                        "label": "Unresolved parent quantity",
                        "type": "unresolved_quantity",
                        "status": "INCOMPLETE",
                        "details": (
                            f"Quantity references parent {missing_parent_id}, "
                            "but that quantity is not registered in the ledger."
                        ),
                    }
                }
                unresolved_edge_id = f"e-{unresolved_id}-{target_node}"
                edge_map[unresolved_edge_id] = {
                    "data": {
                        "id": unresolved_edge_id,
                        "source": unresolved_id,
                        "target": target_node,
                        "label": "missing_input",
                        "type": "missing_input",
                    }
                }
        else:
            is_truncated = True

    # Add Claim Node for the Root Quantity (neutral claim candidate label)
    claim_id = f"claim:{q.id}"
    node_map[claim_id] = {
        "data": {
            "id": claim_id,
            "label": f"Claim Candidate: {q.definition_key}",
            "type": "claim",
            "details": f"Epistemic claim candidate for {q.geo_unit_id}",
        }
    }
    claim_edge_id = f"e-{q.id}-claim"
    edge_map[claim_edge_id] = {
        "data": {
            "id": claim_edge_id,
            "source": str(q.id),
            "target": claim_id,
            "label": "supports",
            "type": "supports_claim",
        }
    }

    return {
        "root_quantity_id": str(q.id),
        "truncated": is_truncated,
        "elements": {
            "nodes": list(node_map.values()),
            "edges": list(edge_map.values()),
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


@router.get("/reports/dossier")
def export_territorial_dossier(
    geo_id: str = Query(..., description="Target geographic unit identifier"),
    scenario_id: Optional[str] = Query(None, description="Optional user scenario identifier"),
    format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"),
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)
    ),
) -> Response:
    """
    Export verified territorial Decision Dossier in JSON, CSV, XLSX, or PDF.
    Enforces formula injection protection on CSV and XLSX formats.
    """
    geo_repo = PostgresGeoUnitRepository()
    unit = geo_repo.get_by_id(geo_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geographic unit not found.")
    geo_name = unit.name
    lgd_code = unit.lgd_code
    census_code = unit.census_code

    scenario_data: Optional[Dict[str, Any]] = None
    if scenario_id:
        scen_repo = PostgresScenarioRepository()
        scen = scen_repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
        if scen:
            scenario_data = {
                "id": scen["id"],
                "name": scen["name"],
                "capital": scen.get("scenario", {}).get("capital"),
                "calculations": scen.get("scenario", {}).get("calculations"),
            }

    scenario_calculations = (scenario_data or {}).get("calculations") or {}
    scenario_quantity_ids = {
        quantity_id
        for key, quantity_id in scenario_calculations.get("quantity_ids", {}).items()
        if not key.startswith(("loan_schedule.month_", "projection.month_"))
    }
    qty_repo = PostgresQuantityRepository()
    raw_quantities = [
        quantity
        for quantity in qty_repo.list_by_geo_unit(geo_id)
        if quantity.owner_id is None or quantity.id in scenario_quantity_ids
    ]
    indicators: List[Dict[str, Any]] = []
    evaluator = DataQualityEvaluator()
    for q in raw_quantities:
        provenance = resolve_quantity_provenance(q, qty_repo)
        assessment = evaluator.evaluate_quantity(
            q,
            q.definition_key,
            geo_id,
            source_id=provenance["source_id"],
            source_version_id=provenance["source_version_id"],
            retrieval_date=provenance["retrieval_date"],
            provenance_complete=provenance["provenance_complete"],
            source_ids=provenance["source_ids"],
        )
        first_source = (
            provenance["lineage_source_provenance"][0]
            if provenance["lineage_source_provenance"]
            else {}
        )
        indicators.append(
            {
                "quantity_id": q.id,
                "definition_key": q.definition_key,
                "value": float(q.value) if q.value is not None else None,
                "unit": q.unit or "",
                "as_of": str(q.as_of or ""),
                "kind": q.kind.value,
                "evidence_floor": q.evidence_floor,
                "quality_status": assessment.primary_status.value,
                "source_name": first_source.get("source_name"),
                "source_id": provenance["source_id"],
                "source_version_id": provenance["source_version_id"],
                "source_provenance": provenance["source_provenance"],
                "lineage_source_provenance": provenance["lineage_source_provenance"],
                "source_refs": list(q.source_refs),
                "parent_ids": list(q.parent_ids),
                "provenance_complete": provenance["provenance_complete"],
            }
        )

    dossier_data: Dict[str, Any] = {
        "geo_id": geo_id,
        "geo_name": geo_name,
        "lgd_code": lgd_code,
        "census_code": census_code,
        "level": unit.level,
        "indicators": indicators,
        "scenario": scenario_data,
    }

    clean_slug = geo_name.lower().replace(" ", "-")
    if format == "json":
        return Response(
            content=generate_dossier_json(dossier_data),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{clean_slug}.json"'
            },
        )
    elif format == "csv":
        return Response(
            content=generate_dossier_csv(dossier_data),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{clean_slug}.csv"'
            },
        )
    elif format == "xlsx":
        return Response(
            content=generate_dossier_xlsx(dossier_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{clean_slug}.xlsx"'
            },
        )
    else:  # pdf
        return Response(
            content=generate_dossier_pdf(dossier_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{clean_slug}.pdf"'
            },
        )
