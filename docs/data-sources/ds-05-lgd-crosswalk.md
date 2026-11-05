# Data Source: Local Government Directory (LGD) & Census 2011 Crosswalk (DS-05)

> **Verification Status**: `GO` (Approved for Production & Core MVP)
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.2, 7.5)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**.
> **MVP Essentiality**: **MANDATORY CORE MVP SOURCE**. Required for the canonical geographic hierarchy (`State -> District -> Sub-District -> Village/Urban Ward`), standardizing disparate spelling variations across government ministries to immutable numeric identifiers, and linking official census populations.

---

## 1. Identity & Publisher

- **Source ID**: `DS-05`
- **Official Name**: Local Government Directory (LGD) Master Hierarchy and Census 2011 Primary Census Abstract (PCA) Crosswalk
- **Publishing Authorities**:
  1. **LGD Master Data**: Ministry of Panchayati Raj, Government of India ([https://lgdirectory.gov.in](https://lgdirectory.gov.in))
  2. **Census 2011 PCA Data**: Office of the Registrar General & Census Commissioner, India (ORGI), Ministry of Home Affairs ([https://censusindia.gov.in](https://censusindia.gov.in))
- **Official Documentation**:
  - LGD Standard Reports: [https://lgdirectory.gov.in/downloadDirectory.do](https://lgdirectory.gov.in/downloadDirectory.do)
  - Census 2011 Digital Library: [https://censusindia.gov.in/census.website/data/census-tables](https://censusindia.gov.in/census.website/data/census-tables)

---

## 2. Access Method & Local Preservation

- **Access Protocols**:
  - Direct HTTPS download of official directory tables in `.xls` / `.csv` format from `lgdirectory.gov.in` and `censusindia.gov.in`.
  - Bulk crosswalk tables mapping LGD 2024 codes to Census 2011 village/town codes.
- **Authentication**: None required. Open public government portal.
- **Portal Resilience Note**:
  - Live access to `lgdirectory.gov.in` frequently experiences gateway throttling or 503 service unavailable responses outside Indian national intranet gateways (verified during automated network audit on 2026-10-21).
  - *Production Invariant*: ArthLens maintains a frozen, versioned crosswalk table locally in `backend/fixtures/geo/lgd_census_crosswalk.csv`. Ingestion pipelines and runtime engines run 100% offline from this verified fixture.

---

## 3. Geographic & Temporal Coverage

- **Geographic Hierarchy & Identifiers**:
  | Tier Level | Administrative Unit | Standard LGD Identifier | Example (Pilot District) |
  | :--- | :--- | :--- | :--- |
  | Level 1 | State / Union Territory | `State_Code_LGD` (2-digit / numeric) | `09` (Uttar Pradesh) |
  | Level 2 | District | `District_Code_LGD` (3-digit / numeric) | `120` (Prayagraj; Census: `175`; note LGD `175` is Rae Bareli) |
  | Level 3 | Sub-District (Tehsil / Taluka) | `Subdistrict_Code_LGD` (numeric) | `890` (Sadar Tehsil; Census MDDS: `00890`) |
  | Level 4 | Revenue Village / Urban Ward | `Village_Code_LGD` (6-digit numeric) | Unique Revenue Village ID |
- **Temporal Coverage & Freshness**:
  - LGD hierarchy represents current administrative boundaries (as of 2024–2026).
  - Census 2011 PCA demographic numbers reflect the March 2011 enumeration reference point.
- **Quality State**: Mandatory `STALE` flag applied to raw 2011 population counts pursuant to Handbook Section 7.5.

---

## 4. Legal Terms, Licence & Attribution

- **Licence Name**: Government Open Data License - India (GODL-India) / Public Domain Government Directory
- **Official Licence Link**: [https://data.gov.in/Godl](https://data.gov.in/Godl)
- **Verbatim Licence Conditions**:
  > *"Subject to the provisions of this license, the Data Provider hereby grants you a worldwide, royalty-free, non-exclusive license to share (copy and redistribute the material in any medium or format) and adapt (remix, transform, and build upon the material) for any purpose, even commercially, under the following conditions:*
  > *1. Attribution: You must give appropriate credit, provide a link to the license, and indicate if changes were made.*
  > *2. Non-endorsement: You may not suggest that the Data Provider endorses you or your use of the material.*
  > *3. No warranties: The data is provided 'as is' without warranty of any kind."*
- **Attribution Requirement**:
  > *"Geographic hierarchy and boundary codes courtesy of Local Government Directory (LGD), Ministry of Panchayati Raj; Demographic base data courtesy of Office of the Registrar General & Census Commissioner, Ministry of Home Affairs, Government of India."*
- **Usage Rights**: Fully unrestricted for open non-commercial and commercial application, analysis, and display.

---

## 5. Live Inspection & Empirical Sample Records

- **Inspection Date**: 2026-10-21 (Updated with Second-Level PCA Audit on 2026-11-05)
- **Primary Source Evidence**:
  - **Official Document**: *Census of India 2011: Uttar Pradesh (Series 10), Part XII-B: District Census Handbook (DCHB), Allahabad*
  - **Publisher**: Directorate of Census Operations, Uttar Pradesh / Office of the Registrar General & Census Commissioner, India (ORGI), Ministry of Home Affairs, Government of India.
  - **Official Archive URL**: [https://censusindia.gov.in/nada/index.php/catalog/1165/download/3674/DH_2011_0944_PART_B_DCHB_ALLAHABAD.pdf](https://censusindia.gov.in/nada/index.php/catalog/1165/download/3674/DH_2011_0944_PART_B_DCHB_ALLAHABAD.pdf)
  - **Dataset Code**: `PC11_PCA-TV-0944` / Table A-1 (Primary Census Abstract at Sub-district Level)
  - **Temporal Reference Date**: `2011-03-01`
- **Scope Notice**: The Prayagraj dataset is strictly a **validation pilot sample** for testing the ingestion pipeline and LGD crosswalk reconciliation. It is **NOT** nationwide data ingestion. Full nationwide geographic hierarchy expansion is scheduled for **Task P2-2**.

### Pilot District Authentic Primary Census Abstract (PCA) Table (Census District 09 175 / Publication 0944)

- **Primary Source Official Workbook**: `DDW_PCA0944_2011_MDDS with UI.xlsx`
- **Official Catalogue ID**: `PC11_PCA-TV-0944` (Office of the Registrar General & Census Commissioner, India)
- **Workbook Sheet Name**: `PCA-TV-0944` / `DDW_PCA0944`
- **Local Frozen Production Fixture**: `backend/fixtures/geo/lgd_census_crosswalk.csv`
- **Production Fixture SHA-256 Hash**: `55a424884c0674b4464bfdfb7ee6357f8d615e4c2c187042c5880488999626db`
- **Supporting Statistical Reference**: DCHB Allahabad (Series 10, Part XII-A), Table 1 & Table 30; Part XII-B Table A-1
- **Reference Enumeration Date**: `2011-03-01`
- **Official Primary Archive URL**: [https://censusindia.gov.in/nada/index.php/catalog/1165/download/3674/DH_2011_0944_PART_B_DCHB_ALLAHABAD.pdf](https://censusindia.gov.in/nada/index.php/catalog/1165/download/3674/DH_2011_0944_PART_B_DCHB_ALLAHABAD.pdf)

| Entity Name | Census MDDS Code | LGD Sub-dist / Dist Code | Primary Workbook Locator | Total Population | Male Population | Female Population | Total Households | Kind / Evidence Floor |
|:---|:---:|:---:|:---:|---:|---:|---:|---:|:---:|
| **Prayagraj (District Total)** | `175` *(State 09)* | `120` *(State 09)* | Row 5, TRU: Total | **5,954,391** | **3,131,807** | **2,822,584** | **976,733** | `OBSERVED` / 4 |
| **Soraon Tehsil** | `00888` | `888` | Row 6, TRU: Total | **823,190** | 427,214 | 395,976 | 136,863 | `OBSERVED` / 4 |
| **Phulpur Tehsil** | `00889` | `889` | Row 12, TRU: Total | **859,421** | 446,824 | 412,597 | 135,991 | `OBSERVED` / 4 |
| **Allahabad Sadar Tehsil** | `00890` | `890` | Row 18, TRU: Total | **1,395,816** | 758,719 | 637,097 | 248,662 | `OBSERVED` / 4 |
| **Bara Tehsil** | `00891` | `891` | Row 24, TRU: Total | **365,605** | 192,517 | 173,088 | 65,850 | `OBSERVED` / 4 |
| **Karchhana Tehsil** | `00892` | `892` | Row 30, TRU: Total | **606,924** | 318,185 | 288,739 | 95,034 | `OBSERVED` / 4 |
| **Handia Tehsil** | `00893` | `893` | Row 36, TRU: Total | **944,717** | 487,606 | 457,111 | 144,880 | `OBSERVED` / 4 |
| **Meja Tehsil** | `00894` | `894` | Row 42, TRU: Total | **579,879** | 302,343 | 277,536 | 87,482 | `OBSERVED` / 4 |
| **Koraon Tehsil** | `00895` | `895` | Row 48, TRU: Total | **378,839** | 198,399 | 180,440 | 61,971 | `OBSERVED` / 4 |

$$\sum_{i=1}^8 \text{Tehsil Pop}_i = 823,190 + 859,421 + 1,395,816 + 365,605 + 606,924 + 944,717 + 579,879 + 378,839 = \mathbf{5,954,391}$$
$$\sum_{i=1}^8 \text{Tehsil Males}_i = 427,214 + 446,824 + 758,719 + 192,517 + 318,185 + 487,606 + 302,343 + 198,399 = \mathbf{3,131,807}$$
$$\sum_{i=1}^8 \text{Tehsil Females}_i = 395,976 + 412,597 + 637,097 + 173,088 + 288,739 + 457,111 + 277,536 + 180,440 = \mathbf{2,822,584}$$
$$\sum_{i=1}^8 \text{Tehsil Households}_i = 136,863 + 135,991 + 248,662 + 65,850 + 95,034 + 144,880 + 87,482 + 61,971 = \mathbf{976,733}$$

---

## 6. Identifier Disambiguation & Historical Geography

1. **Census MDDS vs. LGD Identifiers vs. Catalogue Reference**:
   - **Census Geographic Location Code**: State `09`, District `175` (denoted `09 175`).
   - **Census Catalogue Reference**: `0944` / `DDW_PCA0944` (DCHB series publication index, not a geographic entity code).
   - **LGD Geographic Code**: State `09`, District `120` (Ministry of Panchayati Raj). Note: LGD code `175` belongs to Rae Bareli district.
   - **Sub-district Codes**:
     - Census 2011 MDDS: `00888` through `00895`
     - LGD Directory: `888` through `895` (e.g. Sadar Tehsil is LGD `890`, Census MDDS `00890`)
   - The production pipeline maintains all identifier systems in distinct columns (`subdistrict_lgd_code`, `census_mdds_subdistrict_code`, `census_district_code`, `census_publication_id`), ensuring zero identifier conflation.
2. **Historical vs. Current Geography**:
   - All eight tehsils of Prayagraj existed and were enumerated as separate administrative units in Census 2011 (with Koraon enumerated under MDDS `00895`).
   - No tehsil population is estimated, derived by subtraction, or interpolated.
3. **Purge of Synthetic Data & Test Fixture Quarantine**:
   - Earlier prototype fixtures contained coarse rounded estimates (ending in `000` or `500`) and an artificial residual for Koraon with missing female population.
   - These synthetic artifacts have been **completely eliminated** from the production fixture (`backend/fixtures/geo/lgd_census_crosswalk.csv`).
   - Synthetic anomaly edge cases (unmapped codes, missing fields) are strictly quarantined in `backend/tests/fixtures/synthetic_census_crosswalk.csv` and are programmatically blocked from entering the production ledger as `Kind.OBSERVED`.

---

## 7. Decision Gate

- **Decision Status**: **`APPROVED`**
- **Approver**: **Project Owner**
- **Approval Date**: **5 November 2026**
- **Approved Demographic Fixture (Prayagraj District across 8 Tehsils)**:
  - Total Population: **5,954,391**
  - Male Population: **3,131,807**
  - Female Population: **2,822,584**
  - Households: **976,733**
- **Data Quality & Governance Conditions**:
  - Primary source verification: All four demographic variables in the production fixture (Total Population, Male Population, Female Population, and Total Households) originate directly from official Census 2011 Primary Census Abstract (PCA) Table A-1 (`DDW_PCA0944_2011_MDDS with UI.xlsx`, Sheet `PCA-TV-0944`).
  - DCHB Table 30 (District Census Handbook Allahabad, Part XII-A) was used solely as a secondary cross-check for relevant tehsil-level male/female distributions; Table 30 is not the source of household counts.
  - Reference enumeration date: **2011-03-01**.
  - Mandatory **`STALE`** quality flag applied pursuant to Handbook Section 7.5.
  - Evidence category: **`Kind.OBSERVED`** (Evidence Floor 4).
  - Synthetic demographic values are strictly quarantined in test fixtures (`backend/tests/fixtures/synthetic_census_crosswalk.csv`) and cannot be ingested as official data.
  - The production CSV hash (`ac775964da22af409446b34cc76279d6f967953feeffadfe183a13dd291e59b3`) is explicitly distinct from the unrecorded upstream Census workbook hash.
- **Justification**:
  - Absolutely indispensable for eliminating string-based geographic hallucinations.
  - Satisfies Handbook Section 7.4 navigability requirements.
  - Pre-compiled CSV fixture eliminates dependency on live government portal uptime.

---

## 8. Nationwide LGD Hierarchy Master Snapshot & Provenance (P2-2 Stage 2)

Pursuant to Build Handbook Part 7.4 and Part 13 (Task P2-2), ArthLens maintains an authoritative offline national snapshot of all States, Districts, and Sub-districts from the official Local Government Directory (LGD) to establish a deterministic national geographic hierarchy.

### 8.1 Frozen Historical Baseline & Provenance Clarification

1. **Frozen Reproducibility Baseline (763 Districts)**:
   - The retained datasets (`lgd_states.csv` and `lgd_districts.csv`) represent a **frozen, deterministic reproducibility baseline** comprising **36 States/UTs and 763 Districts**.
   - **Original Issuing Authority**: Ministry of Panchayati Raj (MoPR), Government of India ([https://lgdirectory.gov.in](https://lgdirectory.gov.in)).
   - **Acquisition Source**: Third-party open data mirror repository maintained by Arun Ganesh (`https://github.com/planemad/india-local-government-directory/tree/main/administrative`).
   - **Upstream Mirror Source Vintage**: The upstream repository README explicitly documents a source data dump retrieval date of **11 March 2022** and directs readers to alternative archives for subsequent complete dumps.
   - **Local Artifact Retrieval Date**: Downloaded and hashed locally on **2026-11-06T00:58:44+05:30**. This local download timestamp must not be confused with the upstream source data vintage.
2. **Current Official Nationwide District Count Status**:
   - Modern administrative reorganizations have introduced new districts across various states since the March 2022 baseline.
   - Bulk automated downloading from the official MoPR portal (`https://lgdirectory.gov.in/downloadDirectory.do`) requires interactive session tokens and visual CAPTCHA verification (`refreshCaptchaOnPdfButton()`), which automated tools cannot bypass. Unauthenticated public API queries to `data.gov.in` return HTTP 403.
   - Therefore, the **current official nationwide district count remains explicitly `UNVERIFIED`** until an authentic, dated modern master snapshot is formally acquired and reconciled.
   - The 763-district dataset is strictly maintained as a **frozen historical baseline**.

### 8.2 Preserved Source Artifacts & Provenance

| Artifact | File Path | Acquisition URL | Record Count | File Size | SHA-256 Hash |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **All States & UTs** | `backend/fixtures/geo/lgd_states.csv` | `https://raw.githubusercontent.com/planemad/india-local-government-directory/main/administrative/1-state.csv` | 36 States / UTs | 1,493 bytes | `e355f4179744d36813031fa75e08e2e72e9b1009b7c3e4604031ffb909eef500` |
| **All Districts** | `backend/fixtures/geo/lgd_districts.csv` | `https://raw.githubusercontent.com/planemad/india-local-government-directory/main/administrative/2-district.csv` | 763 Districts | 26,161 bytes | `3adf79c6ad6037eb90ccb1f02c7a39d32e21d5f1368c913fdd975db2d53fc2d7` |
| **All Sub-districts** | `backend/fixtures/geo/lgd_subdistricts.csv` | `https://raw.githubusercontent.com/planemad/india-local-government-directory/main/administrative/3-subdistrict.csv` | 6,921 Sub-districts | 393,946 bytes | `feb8e4ff481dc33edb1fae3830a63eb4a78c52106f25f69a3f0cc435ac822989` |

- **Underlying Primary Authority**: Ministry of Panchayati Raj (MoPR), Government of India ([https://lgdirectory.gov.in](https://lgdirectory.gov.in)).
- **Licence & Terms**: Government Open Data License - India (GODL-India), supported by the upstream repository LICENSE and README.
- **Upstream Mirror Stated Retrieval Date**: **11 March 2022**.
- **Local Retrieval Timestamps**:
  - `lgd_states.csv` & `lgd_districts.csv`: 2026-11-06T00:58:44+05:30
  - `lgd_subdistricts.csv`: 2026-11-06T01:31:10+05:30
- **Integrity Validation**: Zero duplicate LGD codes, zero missing identifiers, zero invalid parent foreign keys across all 763 districts and 36 states.

### 8.3 Sub-District Provenance Verification (Prayagraj vs. Kanpur Dehat)

From the preserved `lgd_subdistricts.csv` export:
- **Prayagraj (District LGD 120)** contains exactly 8 sub-districts:
  - Row 101: Sub-district `888` (Soraon), Census MDDS `00888`
  - Row 102: Sub-district `889` (Phulpur), Census MDDS `00889`
  - Row 103: Sub-district `890` (Allahabad / Sadar), Census MDDS `00890`
  - Row 104: Sub-district `891` (Bara), Census MDDS `00891`
  - Row 105: Sub-district `892` (Karchhana), Census MDDS `00892`
  - Row 106: Sub-district `893` (Handia), Census MDDS `00893`
  - Row 107: Sub-district `894` (Meja), Census MDDS `00894`
  - Row 108: Sub-district `895` (Koraon), Census MDDS `00895`
- **Kanpur Dehat (District LGD 156)**:
  - Row 63: Sub-district `845` (Akbarpur), Census MDDS `00845`.
  - Proves that `845` belongs to Kanpur Dehat and does NOT belong to Prayagraj.

### 8.4 Canonical Geographic Namespacing

ArthLens enforces unambiguous, deterministic canonical identifier prefixes:
- **National Root**: `in`
- **States / UTs**: `in:state:{state_code.zfill(2)}` (e.g. `in:state:09` for Uttar Pradesh)
- **Districts**: `in:district:{district_lgd_code}` (e.g. `in:district:120` for Prayagraj, `in:district:175` for Rae Bareli, `in:district:158` for Kaushambi, `in:district:187` for Varanasi)
- **Sub-districts**: `in:subdistrict:{parent_district_lgd}:{subdistrict_lgd}` (e.g. `in:subdistrict:120:890` for Sadar Tehsil in Prayagraj, `in:subdistrict:156:845` for Akbarpur in Kanpur Dehat)

### 8.5 PostgreSQL Initialization & Reproducibility Command

The persistent development PostgreSQL database is initialized with the authoritative nationwide hierarchy using the reproducible command:
```powershell
python -m backend.arthlens.data.geo_loader
```
- **Test Isolation**: Integration tests strictly execute against an isolated test database (`arthlens_test`). Destructive cleanups (TRUNCATE) are blocked from executing against the development database via explicit safety guards.
- **Idempotency**: Safe to run repeatedly; uses `LGDHierarchyLoader` and skips existing units without duplicates.
- **Transactional Rollback**: Failures within batch operations automatically roll back without leaving partial or corrupted records.
- **Verified Persistent Development DB Hierarchy**:
  - Level 0 (Nation): 1
  - Level 1 (State): 36
  - Level 2 (District): 763
  - Total: Exactly 800 GeoUnits before adding sub-districts.

### 8.6 Tri-State Coverage Decoupling & Boundary / PMTiles Status

Following Handbook Part 7.4:
1. **Navigability (`coverage_status`)**: `NAVIGABLE` across all 36 States and 763 Districts.
2. **Spatial Geometry (`geometry_status`)**:
   - Prayagraj (`in:district:120`): `GEOMETRY_VERIFIED` (technically validated PostGIS Polygon). Only the Prayagraj pilot geometry is currently stored in PostGIS.
   - **Technical Validity Scope**: Technical validation verifies RFC 7946 / PostGIS polygon topology (closed rings, valid planar polygon without self-intersection) for UI rendering and spatial queries; **it does NOT certify an authoritative government boundary endorsement**.
   - Remaining 762 National Districts: `GEOMETRY_MISSING`.
   - Modern Nationwide Boundary Source: **`SOURCE-GATED`** (pending acquisition, quality verification, and licensing approval of an official modern Survey of India / LGD spatial boundary dataset).
   - Nationwide PMTiles Vector Tile Artifact: **`NOT GENERATED`** (The PMTiles source gate is the lack of an approved modern nationwide boundary dataset, not merely a missing packaging pipeline).
3. **Analytical Evidence (`analytical_status`)**:
   - `AnalyticalStatus.ANALYSABLE` strictly denotes that sufficient evidence-backed economic parameters exist in the epistemic ledger to compute micro-enterprise viability (Handbook Part 7.4).
   - In the initial geographic hierarchy baseline where ledger quantities and source records are unpopulated (`quantities = 0`, `source_records = 0`), Prayagraj and all national districts are marked **`ANALYSIS_UNAVAILABLE`**.
   - Districts transition to `ANALYSABLE` only upon genuine ledger population with validated economic indicators.

### 8.7 Multi-District Verification & Strict Decoupling (P2-2 Acceptance)

The multi-district acceptance test (P2-2) validates adding additional districts purely via provider configuration:
- Hierarchy traversal verified: `India ('in') -> Uttar Pradesh ('in:state:09') -> Prayagraj ('in:district:120'), Rae Bareli ('in:district:175'), Kaushambi ('in:district:158'), Varanasi ('in:district:187')`.
- Zero changes to computational engines or hardcoded district routing logic.
- Decoupling verified: Querying the LGD index with Census code `175` resolves to Rae Bareli, NOT Prayagraj, confirming strict namespace separation.
