"""
Source adapters for verified ArthLens data sources (Phase 2, P2-1).
"""

from backend.arthlens.data.adapters.admin_boundaries import AdminBoundariesAdapter
from backend.arthlens.data.adapters.base import SourceAdapter
from backend.arthlens.data.adapters.census_lgd import CensusLGDAdapter
from backend.arthlens.data.adapters.osm import OpenStreetMapAdapter
from backend.arthlens.data.adapters.schemes import SchemeGuidelinesAdapter

__all__ = [
    "SourceAdapter",
    "OpenStreetMapAdapter",
    "CensusLGDAdapter",
    "SchemeGuidelinesAdapter",
    "AdminBoundariesAdapter",
]

