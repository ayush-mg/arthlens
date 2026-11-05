"""
LGD Geographic Hierarchy Loader and District Provider (P2-2 Stage 2).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 9.1, Part 13).
Phase: Phase 2 (P2-2 Stage 2 Nationwide Hierarchy Population).
"""

from dataclasses import dataclass, field
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
    canonical_district_id,
    canonical_nation_id,
    canonical_state_id,
    canonical_subdistrict_id,
)
from backend.arthlens.domain.repositories import GeoUnitRepository


@dataclass(frozen=True)
class DistrictConfig:
    """Configuration/provider specification for registering or expanding a district."""
    name: str
    state_code: str
    lgd_code: str
    census_code: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    navigation_status: NavigationStatus = NavigationStatus.NAVIGABLE
    geometry_status: GeometryStatus = GeometryStatus.GEOMETRY_MISSING
    analytical_status: AnalyticalStatus = AnalyticalStatus.ANALYSIS_UNAVAILABLE


@dataclass
class HierarchyIngestionResult:
    """Summary of nationwide hierarchy ingestion."""
    states_loaded: int = 0
    districts_loaded: int = 0
    total_inserted: int = 0
    total_existing: int = 0
    anomalies: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)


class LGDHierarchyLoader:
    """
    Ingests and reconciles nationwide Local Government Directory (LGD) administrative
    hierarchy into a GeoUnitRepository, enforcing canonical namespacing, parent-child
    relational integrity, and orthogonal coverage semantics.
    """

    def __init__(self, repo: GeoUnitRepository) -> None:
        self.repo = repo

    def ensure_root_nation(self) -> GeoUnit:
        """Ensure canonical Indian national root entity exists."""
        nation = GeoUnit(
            id=canonical_nation_id(),
            parent_id=None,
            level=ResolutionTier.NATION,
            name="India",
            lgd_code="IN",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )
        self.repo.save_unit(nation)
        return nation

    def ingest_district_config(self, config: DistrictConfig) -> GeoUnit:
        """
        Add or update a district entity through pure configuration / provider data
        without hardcoded engine changes (Handbook Section 7.4).
        """
        state_id = canonical_state_id(config.state_code)
        # Ensure parent state exists in repo
        state = self.repo.get_unit(state_id)
        if not state:
            raise ValueError(f"Parent state '{state_id}' does not exist for district '{config.name}' (LGD {config.lgd_code})")

        unit = GeoUnit(
            id=canonical_district_id(config.lgd_code),
            parent_id=state_id,
            level=ResolutionTier.DISTRICT,
            name=config.name.strip(),
            lgd_code=str(config.lgd_code).strip(),
            census_code=str(config.census_code).strip() if config.census_code else None,
            geometry=config.geometry,
            navigation_status=config.navigation_status,
            geometry_status=config.geometry_status,
            analytical_status=config.analytical_status,
        )
        self.repo.save_unit(unit)
        return unit

    def ingest_subdistrict(
        self,
        district_lgd_code: str,
        subdistrict_lgd_code: str,
        name: str,
        census_code: Optional[str] = None,
        navigation_status: NavigationStatus = NavigationStatus.NAVIGABLE,
        geometry_status: GeometryStatus = GeometryStatus.GEOMETRY_MISSING,
        analytical_status: AnalyticalStatus = AnalyticalStatus.ANALYSIS_UNAVAILABLE,
    ) -> GeoUnit:
        """
        Add a subdistrict entity ensuring parent district exists and canonical ID is correctly formatted.
        Enforces that Kanpur Dehat Akbarpur (LGD 845) cannot be assigned to Prayagraj (LGD 120).
        """
        d_code = str(district_lgd_code).strip()
        sd_code = str(subdistrict_lgd_code).strip()

        # Provenance safeguard: Akbarpur (845) belongs to Kanpur Dehat (156), not Prayagraj (120)
        if sd_code == "845" and d_code == "120":
            raise ValueError(
                "Kanpur Dehat Akbarpur (LGD 845) cannot be assigned to Prayagraj (LGD 120). "
                "Official source assigns Akbarpur to Kanpur Dehat (District LGD 156)."
            )

        district_id = canonical_district_id(d_code)
        district = self.repo.get_unit(district_id)
        if not district:
            raise ValueError(f"Parent district '{district_id}' does not exist for sub-district '{name}' (LGD {sd_code})")

        sub_id = canonical_subdistrict_id(d_code, sd_code)
        unit = GeoUnit(
            id=sub_id,
            parent_id=district_id,
            level=ResolutionTier.SUBDISTRICT,
            name=name.strip(),
            lgd_code=sd_code,
            census_code=str(census_code).strip() if census_code else None,
            navigation_status=navigation_status,
            geometry_status=geometry_status,
            analytical_status=analytical_status,
        )
        self.repo.save_unit(unit)
        return unit

    def ingest_national_hierarchy(
        self,
        states_csv_path: Path,
        districts_csv_path: Path,
    ) -> HierarchyIngestionResult:
        """
        Load official national LGD master states and districts from CSV files.
        Idempotent and atomic per batch.
        """
        result = HierarchyIngestionResult()

        # 1. Root nation
        self.ensure_root_nation()

        # 2. States / UTs
        states_units: List[GeoUnit] = []
        with open(states_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_code = (row.get("State Code") or "").strip()
                name = (row.get("State Name") or "").strip()
                census_code = (row.get("Census 2011 Code") or row.get("Census 2001 Code") or "").strip()
                if not raw_code or not name:
                    result.anomalies.append(f"Invalid state row: {row}")
                    continue

                state_id = canonical_state_id(raw_code)
                state_unit = GeoUnit(
                    id=state_id,
                    parent_id=canonical_nation_id(),
                    level=ResolutionTier.STATE,
                    name=name.title(),
                    lgd_code=raw_code,
                    census_code=census_code if census_code else None,
                    navigation_status=NavigationStatus.NAVIGABLE,
                    geometry_status=GeometryStatus.GEOMETRY_MISSING,
                    analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
                )
                states_units.append(state_unit)

        saved_states = self.repo.save_units(states_units)
        result.states_loaded = len(states_units)
        result.total_inserted += saved_states
        result.total_existing += (len(states_units) - saved_states)

        # 3. Districts
        districts_units: List[GeoUnit] = []
        with open(districts_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                state_code = (row.get("State Code") or "").strip()
                district_code = (row.get("District Code") or "").strip()
                name = (row.get("District Name") or "").strip()
                census_code = (row.get("Census 2011 Code") or row.get("Census 2001 Code") or "").strip()

                if not state_code or not district_code or not name:
                    result.anomalies.append(f"Invalid district row: {row}")
                    continue

                state_id = canonical_state_id(state_code)
                # Verify state existence
                if not any(s.id == state_id for s in states_units):
                    result.unresolved.append(f"District {name} (LGD {district_code}) has unknown state {state_code}")
                    continue

                district_id = canonical_district_id(district_code)
                dist_unit = GeoUnit(
                    id=district_id,
                    parent_id=state_id,
                    level=ResolutionTier.DISTRICT,
                    name=name.title(),
                    lgd_code=district_code,
                    census_code=census_code if census_code and census_code != "0" else None,
                    navigation_status=NavigationStatus.NAVIGABLE,
                    geometry_status=GeometryStatus.GEOMETRY_MISSING,
                    analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
                )
                districts_units.append(dist_unit)

        saved_districts = self.repo.save_units(districts_units)
        result.districts_loaded = len(districts_units)
        result.total_inserted += saved_districts
        result.total_existing += (len(districts_units) - saved_districts)

        return result


def init_national_database(
    states_csv: Optional[Path] = None,
    districts_csv: Optional[Path] = None,
    repo: Optional[GeoUnitRepository] = None,
) -> HierarchyIngestionResult:
    """
    Reproducible, idempotent initialization procedure for the PostgreSQL geographic hierarchy.
    Loads official national LGD master states and districts into the database.

    Minimum baseline populated:
    - 1 nation (India, 'in')
    - 36 states / UTs ('in:state:01' .. 'in:state:38')
    - 763 districts ('in:district:{lgd_code}')
    Total: 800 GeoUnits.

    Guarantees:
    - Atomicity per stage with automatic rollback on error.
    - Idempotency: re-running does not duplicate records or fail.
    - Non-destructive: preserves existing geometry and analytical coverage.
    """
    base_fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "geo"
    s_path = states_csv or (base_fixtures / "lgd_states.csv")
    d_path = districts_csv or (base_fixtures / "lgd_districts.csv")

    if not s_path.exists():
        raise FileNotFoundError(f"States master CSV not found at: {s_path}")
    if not d_path.exists():
        raise FileNotFoundError(f"Districts master CSV not found at: {d_path}")

    if repo is None:
        from backend.arthlens.infra.database import get_session_factory
        from backend.arthlens.infra.repositories import PostgresGeoUnitRepository
        repo = PostgresGeoUnitRepository(session_factory=get_session_factory())

    loader = LGDHierarchyLoader(repo=repo)
    return loader.ingest_national_hierarchy(
        states_csv_path=s_path,
        districts_csv_path=d_path,
    )


def main() -> None:
    """CLI entrypoint for nationwide geographic hierarchy initialization."""
    import argparse
    parser = argparse.ArgumentParser(description="ArthLens Nationwide LGD Hierarchy Initializer")
    parser.add_argument("--states-csv", type=Path, default=None, help="Path to states CSV fixture")
    parser.add_argument("--districts-csv", type=Path, default=None, help="Path to districts CSV fixture")
    args = parser.parse_args()

    print("Initializing ArthLens nationwide geographic hierarchy in PostgreSQL...")
    result = init_national_database(
        states_csv=args.states_csv,
        districts_csv=args.districts_csv,
    )
    print(
        f"Initialization complete: {result.states_loaded} states, "
        f"{result.districts_loaded} districts loaded. "
        f"Inserted: {result.total_inserted}, Existing: {result.total_existing}."
    )
    if result.anomalies:
        print(f"Anomalies: {len(result.anomalies)}")
    if result.unresolved:
        print(f"Unresolved: {len(result.unresolved)}")


if __name__ == "__main__":
    main()

