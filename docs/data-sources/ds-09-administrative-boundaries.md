# Data Source: Administrative Boundaries (GIS Polygons & PMTiles) (DS-09)

> **Verification Status**: `APPROVED FOR PRAYAGRAJ PILOT ONLY; MODERN NATIONWIDE BOUNDARIES SOURCE-GATED`
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.2, 7.4)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Pilot boundary is verified for Prayagraj (LGD 120); modern nationwide boundaries remain source-gated pending unauthenticated official programmatic distribution.
> **MVP Essentiality**: **MANDATORY CORE MVP SOURCE FOR PILOT DISTRICT**. Required for rendering vector boundary in MapLibre GL JS, visualizing Prayagraj district boundary, spatial indexing, and PMTiles static tile serving.

---

## 1. Identity & Publisher

- **Source ID**: `DS-09`
- **Official Name**: Administrative Boundary GeoJSON Polygons (Prayagraj Pilot District Baseline)
- **Primary Issuing Authority & Repository**:
  - **Data{Meet} Community Spatial Project**: Open Source GIS Repository for India ([https://github.com/datameet/maps](https://github.com/datameet/maps))
- **Official Documentation**:
  - Data{Meet} Maps Documentation: [http://projects.datameet.org/maps/](http://projects.datameet.org/maps/)

---

## 2. Access Method & Local Preservation

- **Access Protocols**:
  - GeoJSON downloaded from open data repository fixture.
  - Converted via `tippecanoe` into pilot single-file vector archive: **`india_census_2011_pilot.pmtiles`**.
- **Tile Serving Architecture**:
  - PMTiles files are served via HTTP range requests from Cloudflare R2 / S3 object storage (or local FastAPI static file server in development).
  - No active GIS server (GeoServer / MapServer) required, enabling zero-maintenance edge deployment.
- **Authentication**: None required for pilot fixture. Survey of India nationwide portal requires interactive citizen registration/OTP and is source-gated.

---

## 3. Geographic Boundary Delineation (Critical Invariant)

- **Pilot Geographic Granularity**:
  - Prayagraj District Boundary (LGD 120, Census 175): **VERIFIED**.
  - Other 763 Districts: **GEOMETRY_MISSING** (navigable in LGD hierarchy, but boundary vectors are unattached to prevent unverified boundary fabrication).
  - Sub-districts / Tehsils: **GEOMETRY_MISSING** (tabular LGD codes available; boundary geometry source-gated).

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
  > *"Administrative boundaries courtesy of Data{Meet} Community Maps Project (licensed under MIT License) based on Census of India 2011 administrative boundaries."*

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
  - *Resolution*: Mapshaper simplification applied at multiple zoom levels (z0-z5 simplified; z6-z12 high detail) packed into an optimized vector tile archive (`india_census_2011_pilot.pmtiles`, 9,953 bytes for pilot district footprint; future nationwide archive projected at ~45 MB).
- **Fallback Plan**:
  - Pre-generated `india_census_2011_pilot.pmtiles` stored in `backend/fixtures/boundaries/` and mirrored on object storage. Subdistrict/tehsil boundary polygon shapefiles and modern nationwide boundaries remain source-gated pending official Survey of India / UP Revenue Department spatial dataset release.

---

## 7. Decision Gate

- **Decision Status**: **`APPROVED`**
- **Approver**: **Project Owner**
- **Approval Date**: **5 November 2026**
- **Approval Scope & Conditions**:
  - Approved administrative boundary ingestion for the Prayagraj pilot district (LGD 120) based on geometry verification (EPSG:4326 polygon validity) and LGD code reconciliation.
  - The eight constituent tehsils of Prayagraj are approved and ingested as tabular hierarchy records from LGD (`lgd_subdistricts.csv`); however, their spatial boundary polygons are absent from repository fixtures and must be maintained with `geometry_status = 'GEOMETRY_MISSING'` until official cadastral/tehsil vector data is procured.
  - Visual inspection of MapLibre GL JS vector tile rendering is formally completed in Phase 2 Atlas review (Tasks P2-2 / P2-4).
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
   - The pilot district footprint holds a verified spatial polygon boundary for Prayagraj District (LGD 120, `GEOMETRY_VERIFIED`) stored in `backend/fixtures/boundaries/prayagraj_boundaries_sample.geojson`.

### 8.2 Boundary Technical Validation & PMTiles Deliverable Status (P2-2 Complete)

- **Prayagraj Pilot Geometry**: `GEOMETRY_VERIFIED` (RFC 7946 / PostGIS polygon topology, 1,223 vertices, closed coordinate rings, EPSG:4326 WGS-84 reference, valid polygon geometry loaded from `backend/fixtures/boundaries/prayagraj_boundaries_sample.geojson`).
  - **Source Provenance**: Data{Meet} Community Maps Project (Census 2011 vintage baseline, Series 10 Allahabad / Prayagraj LGD 120, Census 175).
  - **License**: Open Database License (ODbL) v1.0 / MIT License.
  - **GeoJSON Checksum (SHA-256)**: `a4ea61c773b99c443bd71a07260881011460eae0600f07be400ef25e2b406c18`.
- **Other 762 National Baseline Districts**: `GEOMETRY_MISSING` (navigable within 800 baseline records, but boundary polygons remain unattached to prevent false Conflation with Census 2011 borders).

### 8.3 Sub-district (Tehsil) Boundary Source Limitation (Prayagraj Pilot Area)

1. **Tabular Hierarchy vs. Spatial Boundary Discrepancy**:
   - `backend/fixtures/geo/lgd_subdistricts.csv` contains all 8 official LGD tehsils for Prayagraj District:
     - Allahabad / Sadar (LGD 890)
     - Bara (LGD 891)
     - Handia (LGD 893)
     - Karchhana (LGD 892)
     - Koraon (LGD 895)
     - Meja (LGD 894)
     - Phulpur (LGD 889)
     - Soraon (LGD 888)
   - These 8 records are ingested into `geo_units` with valid hierarchy parentage (`parent_id = 'in:district:120'`), `level = 4`, and `coverage_status = 'NAVIGABLE'`.
2. **Absence of Tehsil Geometry Fixtures**:
   - `backend/fixtures/boundaries/prayagraj_boundaries_sample.geojson` contains exactly **one single feature**: the district boundary for Prayagraj (`properties: {"dt_cen_cd": 44, "censuscode": 175, "lgd_code": 120}`).
   - No subdistrict or tehsil GIS boundary polygon shapefile or GeoJSON exists in the repository archive.
3. **Strict Epistemic Integrity Enforcement**:
   - In accordance with the Anti-Fabrication invariant (Handbook Part 4.1), ArthLens strictly refrains from fabricating synthetic rectangular boundaries, bounding boxes, or heuristic voronoi partitions for tehsils.
   - All 8 Prayagraj tehsils are persisted with `geometry_status = 'GEOMETRY_MISSING'` and `has_geometry = false`.
   - Any prior documentation passages claiming that 8 tehsil boundary polygons or Sadar Tehsil polygons were already verified and rendered in GIS fixtures were inaccurate and are superseded by this reconciliation. Ingestion of tehsil polygon shapefiles remains source-gated pending official Survey of India or UP Revenue Department release.
- **Survey of India Boundary Portal Investigation (November 2026)**:
  - Portal: `https://onlinemaps.surveyofindia.gov.in/`
  - Catalogue: Administrative Boundary Database (Quick Access) containing National, State, District, and Taluk/Tehsil boundary shapefiles.
  - Legal Terms & National Geospatial Policy: Products are priced at ₹0/- (Free of cost) for Indian citizens and entities for internal/academic/commercial application under national geospatial guidelines.
  - Operational Gate: Access requires individual user registration (mobile OTP / identity verification) and acceptance of end-user license agreements (EULA). Unauthenticated automated scraping or headless CI mirroring is prohibited. Automated nationwide vector ingestion remains explicitly **SOURCE-GATED**.
- **Verified PMTiles Vector Tile Deliverable (Generated & Validated)**:
  - **Archive Path**: `backend/fixtures/boundaries/india_census_2011_pilot.pmtiles`
  - **File Size**: 9,953 bytes
  - **SHA-256 Checksum**: `782659c9e1955c2821d4122c0c4bd2620c90284032f129db5706fccf8367eb4c`
  - **Specification**: PMTiles v3 (MVT Vector Tile Type, GZIP Tile Compression)
  - **Layer Name**: `admin_boundaries` (Description: "Census 2011 district administrative polygons")
  - **Tile Count**: 11 addressed vector tiles spanning Zoom Levels 0 through 8
  - **CRS**: EPSG:4326 (WGS-84 geodetic coordinates)
  - **Bounds**: `[81.520106, 24.807298, 82.353320, 25.751400]`
  - **Feature Count**: 1 (Prayagraj District, LGD 120, Census 175, 1,223 vertices)
  - **Attribution**: Administrative boundaries courtesy of Data{Meet} Community Maps Project (Census 2011 base, licensed under ODbL/MIT), aligned with Survey of India national boundary guidelines.
  - **Verification Status**: Validated using `pmtiles.reader.Reader(MemorySource)` for root tile retrieval, header validity, and metadata deserialization.
  - **Reproducible Generator**: `scripts/generate_pmtiles.py`

When approved nationwide modern shapefiles are acquired, vector tiles will be compiled offline via `tippecanoe` with explicit reproducibility metadata:
- **Target Archive**: `india_boundaries.pmtiles`
- **Tiling Parameters**:
  - Min zoom: `0`, Max zoom: `10`
  - Simplification: Dynamic `--drop-densest-as-needed`
  - Layer names: `nation`, `state`, `district`, `subdistrict`
- **Serving Architecture**: Served strictly as static objects via HTTP range requests from Cloudflare R2 / S3 or FastAPI static mounts; dynamic map-server daemons are strictly prohibited.
