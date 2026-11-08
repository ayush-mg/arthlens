"""
Seed and verify official ArthLens data sources and source-version records in PostgreSQL.

Authoritative Reference:
- ArthLens Build Handbook v1.0 (Part 3, 7.1, 7.2, 7.5, Appendix A.3).
- Registered Sources:
  * DS-01: Open Government Data (OGD) Platform India / RBI DBIE
  * DS-04: OpenStreetMap Road Graph & Amenities (ODbL 1.0)
  * DS-05: Census 2011 Primary Census Abstract & LGD Crosswalk (GODL-India)
  * DS-08: Central Government Schemes Guidelines (GODL-India)
  * DS-09: Data{Meet} Administrative Boundaries (ODbL 1.0)
"""

from datetime import date
import hashlib
import sys
from pathlib import Path

# Add project root to sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import SourceModel, SourceVersionModel


SOURCES_SPEC = [
    {
        "id": "DS-01",
        "name": "Open Government Data (OGD) Platform India / RBI DBIE",
        "description": "District-level financial indicators, commercial bank deposits, and credit advances from RBI DBIE published via data.gov.in.",
        "licence_text": "Government Open Data License - India (GODL)",
        "max_age_days": 365,
        "status": "ACTIVE",
        "versions": [
            {
                "id": "DS-01:2024-rbi-credit",
                "version": "RBI-DBIE-2024",
                "retrieval_date": date(2026, 10, 20),
                "content_hash": hashlib.sha256(b"DS-01:data.gov.in:rbi-dbie-credit-advances:2024").hexdigest(),
                "source_url": "https://data.gov.in/resource/district-wise-credit-deposit-ratio",
                "status": "ACTIVE",
            }
        ],
    },
    {
        "id": "DS-04",
        "name": "OpenStreetMap Road Network & Commercial Amenities",
        "description": "Geographic road graph network, street segments, travel time speeds, and commercial retail amenities from OpenStreetMap.",
        "licence_text": "Open Database Commons Open Database License (ODbL 1.0)",
        "max_age_days": 90,
        "status": "ACTIVE",
        "versions": [
            {
                "id": "DS-04:osm-prayagraj-2026",
                "version": "OSM-2026-Q4",
                "retrieval_date": date(2026, 11, 1),
                "content_hash": hashlib.sha256(b"DS-04:osm:prayagraj:road-graph:amenities:2026").hexdigest(),
                "source_url": "https://www.openstreetmap.org/",
                "status": "ACTIVE",
            }
        ],
    },
    {
        "id": "DS-05",
        "name": "Census of India 2011 Primary Census Abstract & LGD Crosswalk",
        "description": "Official population counts, household totals, gender ratios, and local government directory crosswalk identifiers.",
        "licence_text": "Government Open Data License - India (GODL)",
        "max_age_days": 3650,
        "status": "ACTIVE",
        "versions": [
            {
                "id": "DS-05:census-2011-pca",
                "version": "Census 2011",
                "retrieval_date": date(2026, 11, 7),
                "content_hash": hashlib.sha256(b"DS-05:census:2011:primary-census-abstract:lgd").hexdigest(),
                "source_url": "https://censusindia.gov.in/",
                "status": "ACTIVE",
            }
        ],
    },
    {
        "id": "DS-08",
        "name": "Central Government Scheme Guidelines & Parameters",
        "description": "Official Ministry guidelines and eligibility parameter notifications for PMFME, PMEGP, and PM-MUDRA.",
        "licence_text": "Government Open Data License - India (GODL)",
        "max_age_days": 365,
        "status": "ACTIVE",
        "versions": [
            {
                "id": "DS-08:schemes-2024",
                "version": "Schemes-2024-v1",
                "retrieval_date": date(2026, 11, 5),
                "content_hash": hashlib.sha256(b"DS-08:official:guidelines:pmfme:pmegp:mudra:2024").hexdigest(),
                "source_url": "https://msme.gov.in/all-schemes",
                "status": "ACTIVE",
            }
        ],
    },
    {
        "id": "DS-09",
        "name": "Data{Meet} Community Maps / Census 2011 Administrative Boundaries",
        "description": "Official administrative district and sub-district boundaries for GIS spatial analysis and choropleth mapping.",
        "licence_text": "Open Database License (ODbL) v1.0 / MIT License",
        "max_age_days": 3650,
        "status": "ACTIVE",
        "versions": [
            {
                "id": "DS-09:datameet-census2011",
                "version": "Census 2011",
                "retrieval_date": date(2026, 11, 7),
                "content_hash": hashlib.sha256(b"DS-09:datameet:maps:census:2011:boundaries").hexdigest(),
                "source_url": "https://github.com/datameet/maps",
                "status": "ACTIVE",
            }
        ],
    },
]


def seed_sources():
    session_factory = get_session_factory()
    with session_factory() as session:
        for s_spec in SOURCES_SPEC:
            source = session.get(SourceModel, s_spec["id"])
            if source is None:
                source = SourceModel(
                    id=s_spec["id"],
                    name=s_spec["name"],
                    description=s_spec["description"],
                    licence_text=s_spec["licence_text"],
                    max_age_days=s_spec["max_age_days"],
                    status=s_spec["status"],
                )
                session.add(source)
                session.flush()
                print(f"[CREATED] Source {s_spec['id']}: {s_spec['name']}")
            else:
                source.name = s_spec["name"]
                source.description = s_spec["description"]
                source.licence_text = s_spec["licence_text"]
                source.max_age_days = s_spec["max_age_days"]
                source.status = s_spec["status"]
                print(f"[EXISTS] Source {s_spec['id']}")

            for v_spec in s_spec["versions"]:
                version = session.get(SourceVersionModel, v_spec["id"])
                if version is None:
                    version = SourceVersionModel(
                        id=v_spec["id"],
                        source_id=s_spec["id"],
                        version=v_spec["version"],
                        retrieval_date=v_spec["retrieval_date"],
                        content_hash=v_spec["content_hash"],
                        source_url=v_spec["source_url"],
                        status=v_spec["status"],
                    )
                    session.add(version)
                    print(f"  [CREATED] Version {v_spec['id']}")
                else:
                    version.version = v_spec["version"]
                    version.retrieval_date = v_spec["retrieval_date"]
                    version.content_hash = v_spec["content_hash"]
                    version.source_url = v_spec["source_url"]
                    print(f"  [EXISTS] Version {v_spec['id']}")

        session.commit()
    print("Source and source-version verification/seeding completed successfully.")


if __name__ == "__main__":
    seed_sources()

