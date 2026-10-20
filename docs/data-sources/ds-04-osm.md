# Data Source: OpenStreetMap (OSM) (DS-04)

> **Verification Status**: `GO` (Approved for MVP with Completeness Caveat)
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.2, 7.3)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**.
> **MVP Essentiality**: **MANDATORY CORE MVP SOURCE**. Required for Loop B (Opportunity to Decision): road network extraction, Dijkstra-based travel-time catchment zones (`compute_catchment`), and Point of Interest (POI) competitor counts (`market_competitor_analysis`).

---

## 1. Identity & Publisher

- **Source ID**: `DS-04`
- **Official Name**: OpenStreetMap (OSM) Road Network & Points of Interest (POIs)
- **Publisher / Maintainer**: OpenStreetMap Foundation (OSMF) / Worldwide Open Mapping Community
- **Official Portal URL**: [https://www.openstreetmap.org](https://www.openstreetmap.org)
- **API Documentation & Download Portals**:
  - Overpass API: [https://wiki.openstreetmap.org/wiki/Overpass_API](https://wiki.openstreetmap.org/wiki/Overpass_API)
  - Geofabrik Regional Bulk PBF Extracts (India & Sub-regions): [https://download.geofabrik.de/asia/india.html](https://download.geofabrik.de/asia/india.html)
  - Uttar Pradesh Regional Extract: [https://download.geofabrik.de/asia/india/uttar-pradesh.html](https://download.geofabrik.de/asia/india/uttar-pradesh.html)

---

## 2. Access Method & Authentication

- **Access Protocols**:
  1. **Interactive Query API**: Overpass API interpreter via HTTPS (`https://overpass-api.de/api/interpreter`). Queries written in Overpass QL returning JSON or XML.
  2. **Bulk Vector Extracts**: Protocolbuffer Binary Format (`.osm.pbf`) via Geofabrik daily mirror downloads.
- **Authentication**: None required. Fully open public access.
- **Rate Limits & Governance**:
  - Overpass API enforces slot-based concurrency limits (typically 2 concurrent queries per IP, max 10,000 queries/day). Heavy queries trigger HTTP 429 or 504 gateway timeouts.
  - *Production Invariant*: The production engine must **never** make live unbuffered Overpass API calls during real-time user request loops.
- **Fallback Plan**:
  - Bounding-box clipped road network graph (`.graphml` / NetworkX serialized) and categorized POI GeoJSON fixtures stored locally in repository fixtures (`backend/fixtures/osm/`) and mirrored in S3/Cloudflare R2 object storage. Offline demos run 100% reliably without live Overpass connectivity.

---

## 3. Geographic & Temporal Coverage

- **Geographic Granularity**: Fine-grained point coordinates (lat/lon) for POIs; connected node-way vector topologies for roads.
- **Coverage**: Nationwide across all 28 states and 8 UTs. Tested in pilot district (Prayagraj, Uttar Pradesh).
- **Temporal Freshness**: Continuous real-time community edits; Geofabrik mirrors updated daily (`as_of` date reflects extraction timestamp).
- **Staleness Threshold (`max_age_days`)**: 30 days for bulk road network snapshot updates; 90 days for static fixtures.

---

## 4. Legal Terms, Licence & Attribution

- **Licence Name**: Open Database License (ODbL) 1.0 (Open Data Commons Open Database License)
- **Official Licence Link**: [https://opendatacommons.org/licenses/odbl/1-0/](https://opendatacommons.org/licenses/odbl/1-0/)
- **Verbatim Licence Permissions & Conditions**:
  > *"You are free to Share (copy, distribute and use the database), to Create (produce works from the database), and to Adapt (modify, transform and build upon the database). As long as you:*
  > *1. Attribute: You must attribute any public use of the database, or works produced from the database, in the manner specified in the ODbL.*
  > *2. Share-Alike: If you publicly use any adapted version of this database, or works produced from an adapted database, you must also offer that adapted database under the ODbL.*
  > *3. Keep open: If you redistribute the database, or an adapted version of it, then you may use technological measures that restrict the work (such as DRM) as long as you also make available an equivalent copy without such measures."*
- **Application in ArthLens**:
  - Catchment calculation and demand allocation produce "Produced Works" (analytical reports), which does not trigger the share-alike requirement unless the modified OSM database itself is publicly distributed.
- **Mandatory Attribution String**:
  > *"Map data © OpenStreetMap contributors, available under the Open Database License (ODbL) at https://www.openstreetmap.org/copyright"*

---

## 5. Live Inspection & Verification Findings

- **Inspection Date**: 2026-10-21
- **Inspector**: Automated Technical Audit Pipeline (Task P0-1)
- **Live Endpoint Tested**: OpenStreetMap API v0.6 (`https://api.openstreetmap.org/api/0.6/map`)
- **Bounding Box Sample (Prayagraj Pilot District - Civil Lines / Katra)**:
  - Bounding Box: `min_lon=81.834, min_lat=25.448, max_lon=81.838, max_lat=25.452` (~400m x 400m central commercial grid).
  - Observed Elements: **1,253 Nodes**, **202 Ways**.
- **Sample Empirical Records**:
  ```json
  [
    {
      "type": "node",
      "id": 2057700937,
      "lat": 25.4504642,
      "lon": 81.8363247,
      "tags": {
        "amenity": "fast_food",
        "brand": "McDonald's",
        "cuisine": "burger",
        "name": "McDonald's",
        "takeaway": "yes"
      }
    },
    {
      "type": "node",
      "id": 9994440050,
      "lat": 25.4519162,
      "lon": 81.8341628,
      "tags": {
        "name": "Trends",
        "shop": "clothes",
        "clothes": "women;men;children;fashion"
      }
    },
    {
      "type": "node",
      "id": 10089009816,
      "lat": 25.4497735,
      "lon": 81.8362295,
      "tags": {
        "amenity": "bank",
        "brand": "Central Bank of India",
        "name": "Central Bank of India"
      }
    },
    {
      "type": "node",
      "id": 10089118123,
      "lat": 25.4511357,
      "lon": 81.8343973,
      "tags": {
        "name": "Fiona Diamonds",
        "shop": "jewelry",
        "addr:city": "Prayagraj",
        "addr:district": "Prayagraj",
        "addr:postcode": "211001",
        "addr:street": "Sardar Patel Marg, Civil Lines"
      }
    },
    {
      "type": "way",
      "id": 28785347,
      "tags": {
        "highway": "secondary",
        "surface": "asphalt",
        "oneway": "yes"
      }
    },
    {
      "type": "way",
      "id": 28785511,
      "tags": {
        "highway": "secondary",
        "name": "Subhash Chauraha",
        "surface": "asphalt",
        "oneway": "yes"
      }
    }
  ]
  ```
- **Live Mirror Verification**: Geofabrik regional server verified reachable (`https://download.geofabrik.de/asia/india.html`, HTTP 200). Bulk PBF processing via local snapshot is confirmed as the stable offline fallback.

---

## 6. Known Quality Deficiencies & Resolution Policy

1. **Urban vs. Rural Completeness Asymmetry**:
   - Urban Prayagraj (Civil Lines, Katra, Chowk) has high POI and road density.
   - Peripheral rural tehsils exhibit significant under-reporting of informal micro-enterprises (roadside dhabas, kirana stalls, pushcarts).
   - *Binding Resolution (Handbook Part 2.2, Capability 30)*: ArthLens must prominently render the **OSM Completeness Caveat**:
     > *"Competitor density is derived from OpenStreetMap and reflects mapped physical establishments. Informal, temporary, or unmapped rural vendors may not be captured."*
2. **Topological Disconnections**:
   - Unconnected dead-end ways in rural areas can cause Dijkstra pathfinding to return infinite distance. The graph ingestion pipeline must extract the largest strongly connected component (SCC).

---

## 7. Decision Gate

- **Decision**: **`GO (Approved with Completeness Caveat)`**
- **Justification**:
  - Essential core dependency for Loop B (Dijkstra catchments and competitor density).
  - Open, permissive ODbL license with clear attribution terms.
  - Automated fallback to offline PBF extracts and pre-computed fixtures guarantees 100% demo uptime.
- **Remaining Human Confirmation**: Final sign-off on the exact OSM completeness caveat banner text rendered in the Atlas UI.
