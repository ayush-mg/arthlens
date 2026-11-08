"""Exact source-version provenance resolution for persisted quantities."""

from typing import Any, Dict, List, Set

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity


def resolve_quantity_provenance(
    quantity: Quantity,
    repo: Any,
    _visited: Set[str] | None = None,
) -> Dict[str, Any]:
    """Resolve citations against their exact registered source-version records."""
    from backend.arthlens.infra.models import SourceModel, SourceVersionModel

    visited = set(_visited or ())
    if quantity.id in visited:
        return {
            "source_provenance": [],
            "lineage_source_provenance": [],
            "source_ids": [],
            "source_id": None,
            "source_version_id": None,
            "retrieval_date": None,
            "missing_parent_ids": list(quantity.parent_ids),
            "provenance_complete": False,
        }
    visited.add(quantity.id)

    resolved: List[Dict[str, Any]] = []
    with repo._get_session() as session:
        for reference in quantity.source_refs:
            if isinstance(reference, (tuple, list)):
                version_id = reference[0] if len(reference) >= 1 else None
                locator = reference[1] if len(reference) >= 2 else None
                citation_retrieval_date = reference[2] if len(reference) >= 3 else None
            elif isinstance(reference, dict):
                version_id = reference.get("source_version_id", reference.get("version_id"))
                locator = reference.get("locator")
                citation_retrieval_date = reference.get("retrieval_date")
            else:
                version_id = reference if isinstance(reference, str) else None
                locator = citation_retrieval_date = None

            version_id = str(version_id).strip() if version_id else None
            locator = str(locator).strip() if locator else None
            citation_date = str(citation_retrieval_date)[:10] if citation_retrieval_date else None
            version = session.get(SourceVersionModel, version_id) if version_id else None
            source = session.get(SourceModel, version.source_id) if version else None
            registered_date = version.retrieval_date.isoformat() if version and version.retrieval_date else None
            exact_source_complete = bool(
                version
                and source
                and version.content_hash
                and locator
                and citation_date
                and citation_date == registered_date
            )
            reference_id = str(version_id or "").strip().lower()
            explicit_assumption = bool(
                quantity.kind in {Kind.USER_ASSUMED, Kind.SCENARIO}
                and (reference_id == "user" or reference_id.startswith(("user:", "scenario:")))
                and locator
                and citation_date
            )
            source_display_name = (
                "Office of the Registrar General & Census Commissioner, India"
                if (source and source.id == "DS-05") or (version and version.source_id == "DS-05")
                else (source.name if source else None)
            )
            resolved.append(
                {
                    "source_version_id": version.id if version else None,
                    "source_id": version.source_id if version else None,
                    "source_name": source_display_name,
                    "source_version": version.version if version else None,
                    "source_checksum": version.content_hash if version else None,
                    "locator": locator,
                    "retrieval_date": registered_date if version else citation_date,
                    "provenance_complete": exact_source_complete,
                    "explicit_assumption": explicit_assumption,
                }
            )

    direct_complete = (
        bool(resolved)
        and all(
            item["provenance_complete"] or item["explicit_assumption"]
            for item in resolved
        )
    ) if resolved else bool(quantity.parent_ids)
    parent_quantities = repo.get_parents(quantity.id) if quantity.parent_ids else []
    registered_parent_ids = {parent.id for parent in parent_quantities}
    missing_parent_ids = sorted(set(quantity.parent_ids) - registered_parent_ids)
    parent_results = [
        resolve_quantity_provenance(parent, repo, visited) for parent in parent_quantities
    ]
    parent_complete = not missing_parent_ids and all(
        item["provenance_complete"] for item in parent_results
    )
    complete = direct_complete and parent_complete

    lineage_sources = list(resolved)
    for parent, result in zip(parent_quantities, parent_results):
        for item in result["lineage_source_provenance"]:
            inherited = dict(item)
            inherited.setdefault("quantity_id", parent.id)
            lineage_sources.append(inherited)
    unique_sources: Dict[tuple[str | None, str | None, str | None], Dict[str, Any]] = {}
    for item in lineage_sources:
        key = (
            item.get("source_version_id"),
            item.get("locator"),
            item.get("quantity_id"),
        )
        unique_sources[key] = item
    lineage_sources = list(unique_sources.values())

    direct_ids = [item["source_id"] for item in resolved if item["provenance_complete"]]
    inherited_ids = [
        source_id
        for result in parent_results
        for source_id in result["source_ids"]
    ]
    source_ids = list(dict.fromkeys(direct_ids + inherited_ids))
    primary = next((item for item in resolved if item["provenance_complete"]), None)
    if primary is None:
        primary = next(
            (
                source
                for result in parent_results
                for source in result["lineage_source_provenance"]
                if source.get("provenance_complete")
            ),
            None,
        )
    return {
        "source_provenance": resolved,
        "lineage_source_provenance": lineage_sources,
        "source_ids": source_ids,
        "source_id": primary.get("source_id") if primary else None,
        "source_version_id": primary.get("source_version_id") if primary else None,
        "retrieval_date": primary.get("retrieval_date") if primary else None,
        "missing_parent_ids": missing_parent_ids,
        "provenance_complete": complete,
    }
