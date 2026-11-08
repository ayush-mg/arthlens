"""
Geographic Domain Models and Canonical Namespacing (P2-2.1).

Authoritative Specification: ArthLens Build Handbook v1.0 (Parts 4.3, 5.1, 7.4, 9.1).
Phase: Phase 2 (P2-2.1 - Geographic Hierarchy, Domain Models & Repository Infrastructure).

Provides:
- Immutable GeoUnit domain entity decoupled from database models.
- Canonical geographic namespace formatting (in, in:state, in:district, in:subdistrict).
- Explicit coverage, geometry, and analytical status enums.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from backend.arthlens.domain.enums import ResolutionTier


class NavigationStatus(str, Enum):
    """Status of an administrative entity within the national hierarchy tree."""
    NAVIGABLE = "NAVIGABLE"
    HIERARCHY_UNRESOLVED = "HIERARCHY_UNRESOLVED"


class GeometryStatus(str, Enum):
    """Status of boundary spatial polygon representation."""
    GEOMETRY_VERIFIED = "GEOMETRY_VERIFIED"
    GEOMETRY_SIMPLIFIED = "GEOMETRY_SIMPLIFIED"
    GEOMETRY_HISTORICAL = "GEOMETRY_HISTORICAL"
    GEOMETRY_UNVALIDATED = "GEOMETRY_UNVALIDATED"
    GEOMETRY_MISSING = "GEOMETRY_MISSING"


class AnalyticalStatus(str, Enum):
    """Status of analytical data availability (road graph, POIs, templates)."""
    ANALYSABLE = "ANALYSABLE"
    ANALYSIS_UNAVAILABLE = "ANALYSIS_UNAVAILABLE"


def canonical_nation_id() -> str:
    """Return canonical root identifier for India."""
    return "in"


def canonical_state_id(state_code: str) -> str:
    """Return canonical state identifier with padded 2-digit state code (e.g., 'in:state:09')."""
    cleaned = str(state_code).strip()
    padded = cleaned.zfill(2)
    return f"in:state:{padded}"


def canonical_district_id(district_lgd_code: str) -> str:
    """Return canonical district identifier (e.g., 'in:district:175')."""
    cleaned = str(district_lgd_code).strip()
    return f"in:district:{cleaned}"


def canonical_subdistrict_id(district_lgd_code: str, subdistrict_lgd_code: str) -> str:
    """Return canonical subdistrict identifier (e.g., 'in:subdistrict:156:845' or 'in:subdistrict:120:890')."""
    d_clean = str(district_lgd_code).strip()
    sd_clean = str(subdistrict_lgd_code).strip()
    if not d_clean:
        raise ValueError("Sub-district canonical ID requires a non-empty parent district LGD code.")
    if not sd_clean:
        raise ValueError("Sub-district canonical ID requires a non-empty sub-district LGD code.")
    return f"in:subdistrict:{d_clean}:{sd_clean}"


@dataclass(frozen=True)
class GeoUnit:
    """
    Immutable geographic domain entity representing an administrative unit in the Indian hierarchy.

    Decoupled from SQLAlchemy models and external API schemas.
    """
    id: str
    parent_id: Optional[str]
    level: ResolutionTier
    name: str
    lgd_code: Optional[str] = None
    geometry: Optional[Any] = None  # GeoJSON geometry dict or None
    navigation_status: NavigationStatus = NavigationStatus.NAVIGABLE
    geometry_status: GeometryStatus = GeometryStatus.GEOMETRY_MISSING
    analytical_status: AnalyticalStatus = AnalyticalStatus.ANALYSIS_UNAVAILABLE
    census_code: Optional[str] = None  # Historical Census MDDS code
    geometry_source_record_id: Optional[str] = None  # Exact foreign key linkage to source_records.id

    @property
    def coverage_status(self) -> str:
        """Backward-compatible property mapping to navigation_status value."""
        return self.navigation_status.value

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty or pure whitespace.")

        if self.lgd_code is not None and not str(self.lgd_code).strip():
            raise ValueError("LGD code cannot be empty or pure whitespace.")

        # Validate hierarchy and parent-child consistency
        if self.level == ResolutionTier.NATION:
            if self.id != "in":
                raise ValueError(f"National root entity must have id='in', got '{self.id}'")
            if self.parent_id is not None:
                raise ValueError(f"National root entity must have parent_id=None, got '{self.parent_id}'")

        elif self.level == ResolutionTier.STATE:
            if self.parent_id != "in":
                raise ValueError(f"State level must have nation 'in' as parent, got '{self.parent_id}'")
            if not self.id.startswith("in:state:"):
                raise ValueError(f"State id must start with 'in:state:', got '{self.id}'")

        elif self.level == ResolutionTier.DISTRICT:
            if not self.parent_id or not self.parent_id.startswith("in:state:"):
                raise ValueError(f"District level must have a state parent ('in:state:...'), got '{self.parent_id}'")
            if not self.id.startswith("in:district:"):
                raise ValueError(f"District id must start with 'in:district:', got '{self.id}'")

        elif self.level == ResolutionTier.SUBDISTRICT:
            if not self.parent_id or not self.parent_id.startswith("in:district:"):
                raise ValueError(f"Sub-district level must have a district parent ('in:district:...'), got '{self.parent_id}'")
            if not self.id.startswith("in:subdistrict:"):
                raise ValueError(f"Sub-district id must start with 'in:subdistrict:', got '{self.id}'")

            # Canonical contract: in:subdistrict:{parent_district_lgd}:{subdistrict_lgd}
            parts = self.id.split(":")
            if len(parts) != 4 or not parts[2] or not parts[3]:
                raise ValueError(
                    f"Sub-district id must match 'in:subdistrict:{{parent_district_lgd}}:{{subdistrict_lgd}}' "
                    f"and cannot omit parent district code, got '{self.id}'"
                )

            parent_dist_code = self.parent_id.split(":", 2)[2]
            if parts[2] != parent_dist_code:
                raise ValueError(
                    f"Sub-district id parent district code '{parts[2]}' does not match parent_id '{self.parent_id}'"
                )

            if self.lgd_code is not None and str(self.lgd_code).strip() != parts[3]:
                raise ValueError(
                    f"Sub-district id subdistrict code '{parts[3]}' does not match lgd_code '{self.lgd_code}'"
                )

            # Rejection of Census MDDS codes used as LGD identifiers
            if self.census_code:
                clean_census = str(self.census_code).strip()
                if parts[3] == clean_census and clean_census.startswith("0") and (self.lgd_code is None or str(self.lgd_code).strip() == clean_census):
                    raise ValueError(
                        f"Census MDDS code '{clean_census}' cannot be used as LGD identifier in '{self.id}'. "
                        f"Keep Census codes strictly in 'census_code'."
                    )
                if self.lgd_code and str(self.lgd_code).strip() == clean_census and clean_census.startswith("0"):
                    raise ValueError(
                        f"Census MDDS code '{clean_census}' cannot be used as LGD code. "
                        f"Keep Census codes strictly in 'census_code'."
                    )
            elif parts[3].startswith("00"):
                # 5-digit MDDS codes start with '00' (e.g. 00890, 00845)
                raise ValueError(
                    f"Census MDDS code '{parts[3]}' cannot be used as LGD identifier in '{self.id}'. "
                    f"Keep Census codes strictly in 'census_code'."
                )

        # Geometry consistency
        if self.geometry is not None and self.geometry_status == GeometryStatus.GEOMETRY_MISSING:
            # If geometry is provided without explicit verification status, mark as unvalidated
            object.__setattr__(self, "geometry_status", GeometryStatus.GEOMETRY_UNVALIDATED)
        elif self.geometry is None and self.geometry_status not in (
            GeometryStatus.GEOMETRY_MISSING,
            GeometryStatus.GEOMETRY_HISTORICAL,
        ):
            object.__setattr__(self, "geometry_status", GeometryStatus.GEOMETRY_MISSING)

    def to_dict(self) -> Dict[str, Any]:
        """Convert domain entity to dictionary representation."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "level": int(self.level),
            "name": self.name,
            "lgd_code": self.lgd_code,
            "geometry": self.geometry,
            "navigation_status": self.navigation_status.value,
            "geometry_status": self.geometry_status.value,
            "analytical_status": self.analytical_status.value,
            "coverage_status": self.coverage_status,
            "census_code": self.census_code,
        }

