"""
Abstract Base Class for Source Adapters.

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.5).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.arthlens.data.models import (
    GeographicReconciliation,
    NormalizedRecord,
    ProvenanceMetadata,
    QualityAssessment,
    RawRecord,
)
from backend.arthlens.domain.quantity import Quantity


class SourceAdapter(ABC):
    """
    Abstract contract for human-approved data source adapters.

    Adapters are responsible for:
    1. Schema parsing and validation of external payloads.
    2. Normalization of raw attributes into ArthLens taxonomy.
    3. Geographic reconciliation to LGD codes without fuzzy guessing.
    4. Epistemic extraction of quantities with explicit units.
    """

    source_id: str
    source_name: str
    publisher: str
    official_url: str
    license_name: str
    attribution: str
    max_age_days: int
    as_of_default: Optional[str] = None

    def get_provenance(self) -> ProvenanceMetadata:
        """Return the authoritative legal and attribution metadata for this source."""
        return ProvenanceMetadata(
            source_id=self.source_id,
            source_name=self.source_name,
            publisher=self.publisher,
            official_url=self.official_url,
            license_name=self.license_name,
            attribution=self.attribution,
        )

    @abstractmethod
    def read_local(self, path: Union[Path, str]) -> Any:
        """Read snapshot from a local file path."""
        pass

    @abstractmethod
    def fetch_live(self, params: Dict[str, Any]) -> Any:
        """Fetch snapshot live from the official source endpoint."""
        pass

    @abstractmethod
    def validate_schema(self, raw_content: Any) -> Tuple[bool, List[str]]:
        """Validate input payload against expected schema and integrity constraints."""
        pass

    @abstractmethod
    def parse_records(self, raw_content: Any) -> List[RawRecord]:
        """Parse raw content into unnormalized RawRecord structures."""
        pass

    @abstractmethod
    def normalize_record(self, record: RawRecord) -> NormalizedRecord:
        """Normalize raw attributes while preserving original names, values, and units."""
        pass

    @abstractmethod
    def reconcile_geography(self, record: NormalizedRecord) -> GeographicReconciliation:
        """Reconcile geographic references to official LGD hierarchy."""
        pass

    @abstractmethod
    def extract_quantities(
        self,
        record: NormalizedRecord,
        recon: GeographicReconciliation,
        quality: QualityAssessment,
    ) -> List[Quantity]:
        """Extract immutable Quantity domain models for registration in the ledger."""
        pass

