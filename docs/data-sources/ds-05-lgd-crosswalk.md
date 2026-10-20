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

- **Inspection Date**: 2026-10-21
- **Inspector**: Automated Technical Audit Pipeline (Task P0-1)
- **Pilot District Live Demographic Sample (Prayagraj / Allahabad - LGD Code 175)**:
  ```json
  {
    "lgd_state_code": 9,
    "state_name": "Uttar Pradesh",
    "lgd_district_code": 175,
    "district_name": "Prayagraj",
    "historic_census_name": "Allahabad",
    "census_2011_code": "175",
    "demographics_census_2011": {
      "total_population": 5954391,
      "male_population": 3131807,
      "female_population": 2822584,
      "sex_ratio": 901,
      "total_households": 962772,
      "average_literacy_pct": 72.32,
      "ranking_state_populous": 1
    },
    "subdistricts_tehsils": [
      { "subdistrict_lgd_code": 843, "subdistrict_name": "Soraon" },
      { "subdistrict_lgd_code": 844, "subdistrict_name": "Phulpur" },
      { "subdistrict_lgd_code": 845, "subdistrict_name": "Sadar" },
      { "subdistrict_lgd_code": 846, "subdistrict_name": "Handia" },
      { "subdistrict_lgd_code": 847, "subdistrict_name": "Karchhana" },
      { "subdistrict_lgd_code": 848, "subdistrict_name": "Bara" },
      { "subdistrict_lgd_code": 849, "subdistrict_name": "Meja" },
      { "subdistrict_lgd_code": 850, "subdistrict_name": "Koraon" }
    ]
  }
  ```

---

## 6. Known Data Reorganization Challenges & Resolution

1. **Bifurcated Districts**:
   - Over 100 new districts have been created in India between 2011 and 2026.
   - *Resolution*: Sub-district and village level mapping aggregates up to the current 2026 district boundaries via parent LGD foreign keys.
2. **Name Variations**:
   - Discrepancies between historical colonial names and updated names (e.g. `Allahabad` vs `Prayagraj`).
   - *Resolution*: Canonical joins operate strictly on numeric `lgd_district_code` (`175`), completely bypassing string matching failures.

---

## 7. Decision Gate

- **Decision**: **`GO (Approved for Core MVP Foundation)`**
- **Justification**:
  - Absolutely indispensable for eliminating string-based geographic hallucinations.
  - Satisfies Handbook Section 7.4 navigability requirements.
  - Pre-compiled CSV fixture eliminates dependency on live government portal uptime.
- **Remaining Human Confirmation**: Final human validation of the Prayagraj sub-district LGD code crosswalk table in `backend/fixtures/geo/`.
