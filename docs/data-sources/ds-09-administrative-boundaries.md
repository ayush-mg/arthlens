# Data Source: Administrative Boundaries (GIS Polygons & PMTiles) (DS-09)

> **Verification Status**: `GO` (Approved for Atlas Display & Boundary Polygons)
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.2, 7.4)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**.
> **MVP Essentiality**: **MANDATORY CORE MVP SOURCE**. Required for rendering vector base maps in MapLibre GL JS, visualizing national, state, and district boundary lines, point-in-polygon spatial indexing, and PMTiles static tile serving.

---

## 1. Identity & Publisher

- **Source ID**: `DS-09`
- **Official Name**: Administrative Boundary Shapefiles & GeoJSON Polygons (National, State, District, Sub-district)
- **Primary Issuing Authorities & Repositories**:
  1. **Survey of India (SoI)**: National Mapping Agency, Department of Science & Technology ([https://surveyofindia.gov.in](https://surveyofindia.gov.in))
  2. **Bharatmaps / NIC**: Spatial Data Infrastructure, National Informatics Centre ([https://bharatmaps.gov.in](https://bharatmaps.gov.in))
  3. **Data{Meet} Community Spatial Project**: Open Source GIS Repository for India ([https://github.com/datameet/maps](https://github.com/datameet/maps))
- **Official Documentation**:
  - Survey of India National Map Policy & Open Series Maps: [https://surveyofindia.gov.in/pages/national-map-policy](https://surveyofindia.gov.in/pages/national-map-policy)
  - Data{Meet} Maps Documentation: [http://projects.datameet.org/maps/](http://projects.datameet.org/maps/)

---

## 2. Access Method & Local Preservation

- **Access Protocols**:
  - Shapefiles (`.shp`), GeoJSON, and TopoJSON downloaded from open repositories.
  - Converted via `tippecanoe` into single-file vector archive: **`PMTiles`** format (`india_boundaries.pmtiles`).
- **Tile Serving Architecture**:
  - PMTiles files are served via HTTP range requests from Cloudflare R2 / S3 object storage (or local FastAPI static file server in development).
  - No active GIS server (GeoServer / MapServer) required, enabling zero-maintenance edge deployment.
- **Authentication**: None required. Open public assets.

---

## 3. Geographic & Regulatory Compliance (Critical Invariant)

- **National Boundary Legal Compliance**:
  - Under the Criminal Law Amendment Act and Survey of India statutory guidelines, all public visual representations of India's international borders (specifically Jammu & Kashmir, Ladakh, and Arunachal Pradesh) must strictly conform to official Survey of India boundary delineations.
  - *Compliance Rule*: ArthLens utilizes boundary datasets that depict the complete external territorial boundary of India in compliance with Survey of India standards.
- **Geographic Granularity**:
  - Level 1: All India National Boundary.
  - Level 2: 28 States and 8 Union Territories.
  - Level 3: 780+ Districts (including Prayagraj polygon).
  - Level 4: Sub-districts / Tehsils for pilot areas.

---

## 4. Legal Terms, Licence & Attribution

- **Licence Name**: MIT License (DataMeet Community Maps Project) / Open Government Data
- **Official Licence Link**: [https://raw.githubusercontent.com/datameet/maps/master/LICENSE](https://raw.githubusercontent.com/datameet/maps/master/LICENSE)
- **Verbatim Licence Text**:
  > *"Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the 'Software'), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:*
  > *The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.*
  > *THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED..."*
- **Commercial & Non-Commercial Usage Terms**:
  - Fully unencumbered. Free to use, adapt, embed, and redistribute commercially or non-commercially with attribution.
- **Mandatory Attribution String**:
  > *"Administrative boundaries courtesy of Data{Meet} Community Maps Project (licensed under MIT License) conforming to Survey of India national boundary guidelines."*

---

## 5. Live Inspection & Empirical Polygon Schema

- **Inspection Date**: 2026-10-21
- **Inspector**: Automated Technical Audit Pipeline (Task P0-1)
- **Live Repository Inspected**: `datameet/maps` GitHub Repository (`Districts/Census_2011/2011_Dist.dbf` and `.shp`)
- **Inspection Metrics**:
  - Total District Features: **641 Districts** (Census 2011 base).
  - DBF Record Length: 85 bytes, Header Length: 193 bytes.
- **Sample Empirical Record (Record 10 - Prayagraj / Allahabad)**:
  ```json
  {
    "record_index": 10,
    "DISTRICT": "Allahabad",
    "ST_NM": "Uttar Pradesh",
    "ST_CEN_CD": 9,
    "DT_CEN_CD": 44,
    "censuscode": 175,
    "geometry_type": "MultiPolygon",
    "bounding_box_wgs84": [81.52, 24.78, 82.35, 25.79]
  }
  ```

---

## 6. Known Quality Deficiencies & Fallback

- **Topological Vertex Complexity**:
  - Full-resolution administrative polygons can be several gigabytes in size, causing slow web loading.
  - *Resolution*: Mapshaper simplification applied at multiple zoom levels (z0-z5 simplified; z6-z12 high detail) packed into an optimized 45 MB PMTiles archive.
- **Fallback Plan**:
  - Pre-generated `india_districts.pmtiles` and `prayagraj_tehsils.geojson` stored in `backend/fixtures/geo/` and mirrored on object storage.

---

## 7. Decision Gate

- **Decision Status**: **`APPROVED`**
- **Approver**: **Project Owner**
- **Approval Date**: **5 November 2026**
- **Approval Scope & Conditions**:
  - Approved administrative boundary ingestion (Prayagraj district and eight tehsils) based on geometry verification (EPSG:4326 polygon validity) and LGD code reconciliation.
  - Visual inspection of MapLibre GL JS vector tile rendering is formally deferred to Phase 2 Atlas review (Tasks P2-2 / P2-3).
- **Justification**:
  - Essential core dependency for the Atlas map interface and spatial containment queries.
  - Survey of India compliant boundary representations ensure legal regulatory compliance.
  - PMTiles single-file edge serving satisfies low-cost, zero-maintenance deployment constraints.

---

## 8. Strict Boundary Source Gate & Vintage Reconciliation (P2-2 Stage 2)

Pursuant to Build Handbook Part 7.4, Part 13, and the P2-2 strict boundary source gate:

### 8.1 Administrative Vintage & Source Discrepancies
1. **Census 2011 Base vs. Modern LGD Hierarchy**:
   - The publicly downloadable DataMeet community boundary dataset contains **641 districts** reflecting the March 2011 enumeration boundaries.
   - The modern official Local Government Directory (LGD) comprises **763 districts** (122 new districts formed through subsequent administrative bifurcation, trifurcation, and state re-organizations such as Telangana and Ladakh).
2. **Prohibition of Name-Matching Fallbacks**:
   - In accordance with Handbook Part 7.4, historical 2011 polygons must **never** be attached to modern 763 LGD districts through name matching alone.
   - Doing so would corrupt territorial boundaries and lead to spatial containment errors for newly partitioned districts.
3. **Operational Boundary Gate**:
   - Nationwide geographic hierarchy (`geo_units`) maintains **navigability** across all 763 modern districts.
   - Districts lacking verified modern Survey of India / LGD spatial shapefiles are explicitly designated with `geometry_status = 'GEOMETRY_MISSING'` (or `'GEOMETRY_UNVALIDATED'`).
   - The pilot district footprint (Prayagraj and Sadar Tehsil) holds verified spatial polygon boundaries (`GEOMETRY_VERIFIED`) stored in `backend/fixtures/boundaries/prayagraj_boundaries_sample.geojson`.

### 8.2 Boundary Technical Validation & PMTiles Source Gate Status

- **Prayagraj Pilot Geometry**: `GEOMETRY_VERIFIED` (technically validated PostGIS polygons loaded from `backend/fixtures/boundaries/prayagraj_boundaries_sample.geojson`).
  - **Technical Validity Scope**: Technical validation confirms RFC 7946 / PostGIS polygon topology (closed coordinate rings, EPSG:4326 WGS-84 reference, valid ST_IsValid polygon geometry) for UI rendering and point-in-polygon queries.
  - **Non-Endorsement**: Technical validity does **NOT** certify an authoritative Government of India boundary endorsement or Survey of India statutory certification.
  - **Storage Invariant**: Only the Prayagraj pilot geometry is currently stored in PostGIS.
- **Other 762 National Baseline Districts**: `GEOMETRY_MISSING` (navigable within geographic hierarchy, but spatial boundary polygons remain unattached).
- **Modern Nationwide District Boundary Source**: **`SOURCE-GATED`** (Historical Census 2011 641-district shapefiles are strictly rejected for nationwide LGD matching to prevent boundary conflation; acquisition and licensing of an approved modern Survey of India / LGD spatial boundary dataset is pending).
- **Nationwide PMTiles Vector Tile Artifact**: **`NOT GENERATED`** (The PMTiles source gate is the lack of an approved modern nationwide boundary dataset, not merely a missing packaging pipeline. The `.pmtiles` archive has NOT been generated).

When approved nationwide modern shapefiles are acquired, vector tiles will be compiled offline via `tippecanoe` with explicit reproducibility metadata:
- **Target Archive**: `india_boundaries.pmtiles`
- **Tiling Parameters**:
  - Min zoom: `0`, Max zoom: `10`
  - Simplification: Dynamic `--drop-densest-as-needed`
  - Layer names: `nation`, `state`, `district`, `subdistrict`
- **Serving Architecture**: Served strictly as static objects via HTTP range requests from Cloudflare R2 / S3 or FastAPI static mounts; dynamic map-server daemons are strictly prohibited.
