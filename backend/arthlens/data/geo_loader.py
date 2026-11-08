"""
LGD Geographic Hierarchy Loader and District Provider (P2-2 Stage 2).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 9.1, Part 13).
Phase: Phase 2 (P2-2 Stage 2 Nationwide Hierarchy Population).
"""

from dataclasses import dataclass, field
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

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
    """Summary of nationwide hierarchy ingestion and boundary reconciliation."""
    states_loaded: int = 0
    districts_loaded: int = 0
    subdistricts_loaded: int = 0
    total_inserted: int = 0
    total_existing: int = 0
    anomalies: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    boundary_result: Optional[Any] = None
    coverage_summary: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_units(self) -> int:
        return self.total_inserted + self.total_existing + 1

    @property
    def state_count(self) -> int:
        return self.states_loaded

    @property
    def district_count(self) -> int:
        return self.districts_loaded

    @property
    def subdistrict_count(self) -> int:
        return self.subdistricts_loaded


NationalInitializationReport = HierarchyIngestionResult


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

    def ingest_administrative_boundaries(
        self,
        boundaries_path: Union[Path, str],
        is_local: bool = True,
        default_vintage: str = "Census 2011",
        as_of: str = "2011-03-01",
    ) -> Any:
        """
        Stage 2: Reconcile and enrich administrative boundary polygons into PostGIS
        with full spatial and cryptographic validation (PostGIS ST_IsValid, AABB rejection).
        """
        from backend.arthlens.data.adapters.admin_boundaries import AdminBoundaryIngestionService
        from backend.arthlens.infra.database import get_session_factory
        service = AdminBoundaryIngestionService(
            session_factory=get_session_factory(),
            geo_repo=self.repo,
        )
        return service.ingest_boundaries(
            source_input=boundaries_path,
            is_local=is_local,
            default_vintage=default_vintage,
            as_of=as_of,
        )

    def ingest_national_hierarchy(
        self,
        states_csv_path: Path,
        districts_csv_path: Path,
        subdistricts_csv_path: Optional[Path] = None,
    ) -> HierarchyIngestionResult:
        """
        Load official national LGD master states, districts, and approved subdistricts from CSV files.
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

        # 4. Subdistricts (P2-2 nationwide approved subdistricts)
        if subdistricts_csv_path and Path(subdistricts_csv_path).exists():
            subdistricts_units: List[GeoUnit] = []
            known_district_ids = {d.id for d in districts_units}
            with open(subdistricts_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    dist_code = (row.get("District Code") or "").strip()
                    subdist_code = (row.get("Sub-district Code") or "").strip()
                    subdist_name = (row.get("Sub-district Name") or "").strip()
                    census_code = (row.get("Census 2011 code") or row.get("Census 2001 code") or "").strip()
                    if census_code in ("", "0", "00000"):
                        census_code = None

                    if not dist_code or not subdist_code or not subdist_name:
                        result.anomalies.append(f"Invalid subdistrict row: {row}")
                        continue

                    # Provenance safeguard: Akbarpur (845) belongs to Kanpur Dehat (156), not Prayagraj (120)
                    if subdist_code == "845" and dist_code == "120":
                        result.anomalies.append("Akbarpur 845 cannot be assigned to Prayagraj 120.")
                        continue

                    parent_dist_id = canonical_district_id(dist_code)
                    if parent_dist_id not in known_district_ids:
                        result.unresolved.append(f"Subdistrict {subdist_name} has unknown district {dist_code}")
                        continue

                    sub_id = canonical_subdistrict_id(dist_code, subdist_code)
                    sub_unit = GeoUnit(
                        id=sub_id,
                        parent_id=parent_dist_id,
                        level=ResolutionTier.SUBDISTRICT,
                        name=subdist_name.title(),
                        lgd_code=subdist_code,
                        census_code=census_code,
                        navigation_status=NavigationStatus.NAVIGABLE,
                        geometry_status=GeometryStatus.GEOMETRY_MISSING,
                        analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
                    )
                    subdistricts_units.append(sub_unit)

            saved_subdistricts = self.repo.save_units(subdistricts_units)
            result.subdistricts_loaded = len(subdistricts_units)
            result.total_inserted += saved_subdistricts
            result.total_existing += (len(subdistricts_units) - saved_subdistricts)

        return result


def init_national_database(
    states_csv: Optional[Path] = None,
    districts_csv: Optional[Path] = None,
    subdistricts_csv: Optional[Path] = None,
    boundaries_path: Optional[Union[Path, str]] = None,
    repo: Optional[GeoUnitRepository] = None,
    skip_boundaries: bool = False,
    include_subdistricts: bool = True,
) -> HierarchyIngestionResult:
    """
    Reproducible, idempotent multistage initialization procedure for the PostgreSQL geographic foundation.

    Required sequence (Build Handbook P2-1/P2-2):
    1. Load official LGD geographic hierarchy (1 nation, 36 states, 763 districts, 6,921 subdistricts).
    2. Reconcile approved boundary dataset against the hierarchy (PostGIS ST_IsValid, AABB rejection).
    3. Validate candidate geometries and persist valid geometries & provenance.
    4. Preserve missing and unresolved states accurately without fabricated coordinates.
    5. Generate nationwide coverage report.
    """
    base_fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "geo"
    s_path = states_csv or (base_fixtures / "lgd_states.csv")
    d_path = districts_csv or (base_fixtures / "lgd_districts.csv")
    sd_path = subdistricts_csv or (base_fixtures / "lgd_subdistricts.csv") if include_subdistricts else None

    if not s_path.exists():
        raise FileNotFoundError(f"States master CSV not found at: {s_path}")
    if not d_path.exists():
        raise FileNotFoundError(f"Districts master CSV not found at: {d_path}")

    if repo is None:
        from backend.arthlens.infra.database import get_session_factory
        from backend.arthlens.infra.repositories import PostgresGeoUnitRepository
        repo = PostgresGeoUnitRepository(session_factory=get_session_factory())

    loader = LGDHierarchyLoader(repo=repo)
    result = loader.ingest_national_hierarchy(
        states_csv_path=s_path,
        districts_csv_path=d_path,
        subdistricts_csv_path=sd_path if sd_path and sd_path.exists() else None,
    )

    # Stage 2: Administrative boundaries enrichment
    if not skip_boundaries:
        b_path = boundaries_path
        if b_path is None:
            default_fixture = Path(__file__).resolve().parents[2] / "fixtures" / "boundaries" / "prayagraj_boundaries_sample.geojson"
            if default_fixture.exists():
                b_path = default_fixture

        if b_path:
            boundary_res = loader.ingest_administrative_boundaries(boundaries_path=b_path)
            result.boundary_result = boundary_res

    # Stage 3: Nationwide coverage summary
    if hasattr(repo, "get_coverage_summary"):
        result.coverage_summary = repo.get_coverage_summary()

    return result


def main() -> None:
    """CLI entrypoint for nationwide geographic hierarchy and boundary initialization."""
    import argparse
    parser = argparse.ArgumentParser(description="ArthLens Nationwide LGD Hierarchy and Boundary Initializer")
    parser.add_argument("--states-csv", type=Path, default=None, help="Path to states CSV fixture")
    parser.add_argument("--districts-csv", type=Path, default=None, help="Path to districts CSV fixture")
    parser.add_argument("--boundaries-path", type=Path, default=None, help="Path to approved boundary GeoJSON")
    parser.add_argument("--skip-boundaries", action="store_true", help="Skip boundary enrichment stage")
    args = parser.parse_args()

    print("Initializing ArthLens nationwide geographic hierarchy in PostgreSQL...")
    result = init_national_database(
        states_csv=args.states_csv,
        districts_csv=args.districts_csv,
        boundaries_path=args.boundaries_path,
        skip_boundaries=args.skip_boundaries,
    )
    print(
        f"Hierarchy stage complete: {result.states_loaded} states, "
        f"{result.districts_loaded} districts loaded. "
        f"Inserted: {result.total_inserted}, Existing: {result.total_existing}."
    )
    if result.boundary_result:
        b = result.boundary_result
        print(
            f"Boundary stage complete: {b.total_features} features, "
            f"{b.valid_geometries} valid, {b.invalid_geometries} invalid, "
            f"{b.persisted_geometries} persisted, {b.preserved_existing_geometries} preserved."
        )
    if result.coverage_summary:
        print("Coverage Summary:", result.coverage_summary)
    if result.anomalies:
        print(f"Anomalies: {len(result.anomalies)}")
    if result.unresolved:
        print(f"Unresolved: {len(result.unresolved)}")


if __name__ == "__main__":
    main()

