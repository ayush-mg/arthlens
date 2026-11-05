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
  | Level 2 | District | `District_Code_LGD` (3-digit / numeric) | `175` (Prayagraj / Allahabad) |
  | Level 3 | Sub-District (Tehsil / Taluka) | `Subdistrict_Code_LGD` (numeric) | `00845` (Sadar Tehsil) |
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
- **Production Fixture SHA-256 Hash**: `ac775964da22af409446b34cc76279d6f967953feeffadfe183a13dd291e59b3`
- **Supporting Statistical Reference**: DCHB Allahabad (Series 10, Part XII-A), Table 1 & Table 30; Part XII-B Table A-1
- **Reference Enumeration Date**: `2011-03-01`
- **Official Primary Archive URL**: [https://censusindia.gov.in/nada/index.php/catalog/1165/download/3674/DH_2011_0944_PART_B_DCHB_ALLAHABAD.pdf](https://censusindia.gov.in/nada/index.php/catalog/1165/download/3674/DH_2011_0944_PART_B_DCHB_ALLAHABAD.pdf)

| Entity Name | Census MDDS Code | LGD Sub-dist Code | Primary Workbook Locator | Total Population | Male Population | Female Population | Total Households | Kind / Evidence Floor |
|:---|:---:|:---:|:---:|---:|---:|---:|---:|:---:|
| **Prayagraj (District Total)** | `175` *(State 09)* | `175` *(State 09)* | Row 5, TRU: Total | **5,954,391** | **3,131,807** | **2,822,584** | **976,733** | `OBSERVED` / 4 |
| **Soraon Tehsil** | `00888` | `00843` | Row 6, TRU: Total | **823,190** | 427,214 | 395,976 | 136,863 | `OBSERVED` / 4 |
| **Phulpur Tehsil** | `00889` | `00844` | Row 12, TRU: Total | **859,421** | 446,824 | 412,597 | 135,991 | `OBSERVED` / 4 |
| **Allahabad Sadar Tehsil** | `00890` | `00845` | Row 18, TRU: Total | **1,395,816** | 758,719 | 637,097 | 248,662 | `OBSERVED` / 4 |
| **Bara Tehsil** | `00891` | `00848` | Row 24, TRU: Total | **365,605** | 192,517 | 173,088 | 65,850 | `OBSERVED` / 4 |
| **Karchhana Tehsil** | `00892` | `00847` | Row 30, TRU: Total | **606,924** | 318,185 | 288,739 | 95,034 | `OBSERVED` / 4 |
| **Handia Tehsil** | `00893` | `00846` | Row 36, TRU: Total | **944,717** | 487,606 | 457,111 | 144,880 | `OBSERVED` / 4 |
| **Meja Tehsil** | `00894` | `00849` | Row 42, TRU: Total | **579,879** | 302,343 | 277,536 | 87,482 | `OBSERVED` / 4 |
| **Koraon Tehsil** | `00895` | `00850` | Row 48, TRU: Total | **378,839** | 198,399 | 180,440 | 61,971 | `OBSERVED` / 4 |

$$\sum_{i=1}^8 \text{Tehsil Pop}_i = 823,190 + 859,421 + 1,395,816 + 365,605 + 606,924 + 944,717 + 579,879 + 378,839 = \mathbf{5,954,391}$$
$$\sum_{i=1}^8 \text{Tehsil Males}_i = 427,214 + 446,824 + 758,719 + 192,517 + 318,185 + 487,606 + 302,343 + 198,399 = \mathbf{3,131,807}$$
$$\sum_{i=1}^8 \text{Tehsil Females}_i = 395,976 + 412,597 + 637,097 + 173,088 + 288,739 + 457,111 + 277,536 + 180,440 = \mathbf{2,822,584}$$
$$\sum_{i=1}^8 \text{Tehsil Households}_i = 136,863 + 135,991 + 248,662 + 65,850 + 95,034 + 144,880 + 87,482 + 61,971 = \mathbf{976,733}$$

---

## 6. Identifier Disambiguation & Historical Geography

1. **Census MDDS vs. LGD Identifiers vs. Catalogue Reference**:
   - **Census Geographic Location Code**: State `09`, District `175` (denoted `09 175`).
   - **Census Catalogue Reference**: `0944` / `DDW_PCA0944` (DCHB series publication index, not a geographic entity code).
   - **LGD Geographic Code**: State `09`, District `175` (Ministry of Panchayati Raj).
   - **Sub-district Codes**:
     - Census 2011 MDDS: `00888` through `00895`
     - LGD Directory: `00843` through `00850`
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
  - Verified against official Census 2011 Primary Census Abstract Table A-1 and District Census Handbook Table 30.
  - Reference enumeration date: **2011-03-01**.
  - Mandatory **`STALE`** quality flag applied pursuant to Handbook Section 7.5.
  - Evidence category: **`Kind.OBSERVED`** (Evidence Floor 4).
  - Synthetic demographic values are strictly quarantined in test fixtures (`backend/tests/fixtures/synthetic_census_crosswalk.csv`) and cannot be ingested as official data.
  - The production CSV hash (`ac775964da22af409446b34cc76279d6f967953feeffadfe183a13dd291e59b3`) is explicitly distinct from the unrecorded upstream Census workbook hash.
- **Justification**:
  - Absolutely indispensable for eliminating string-based geographic hallucinations.
  - Satisfies Handbook Section 7.4 navigability requirements.
  - Pre-compiled CSV fixture eliminates dependency on live government portal uptime.
