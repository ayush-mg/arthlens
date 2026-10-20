# Data Source: Socioeconomic High-resolution Rural-Urban Geographic Platform (SHRUG) (DS-03)

> **Verification Status**: `DEFERRED / CONDITIONAL NO-GO (Deferred from Initial MVP)`
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.4, 13.1)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**.
> **MVP Essentiality**: **NON-ESSENTIAL / DEFERRED**. Initially considered for village-level population and non-farm economic census establishment counts. Deferred due to licensing constraints and extreme demographic staleness.

---

## 1. Identity & Publisher

- **Source ID**: `DS-03`
- **Official Name**: SHRUG (Socioeconomic High-resolution Rural-Urban Geographic Platform for India)
- **Publisher / Maintainer**: Development Data Lab (DDL) (Paul Novosad, Sam Asher, et al.)
- **Official Portal URL**: [https://www.devdatalab.org/shrug](https://www.devdatalab.org/shrug)
- **Data Documentation**: [https://www.devdatalab.org/shrug-download](https://www.devdatalab.org/shrug-download)

---

## 2. Access Method & Authentication

- **Access Protocols**: Direct download of zipped CSV / Stata (`.dta`) / R data tables via web forms from DevDataLab.
- **Authentication**: Email registration required on portal. No open REST API endpoint exists.
- **Data Layout**: Tabular datasets linked via unique geographic keys (`shrid`).

---

## 3. Geographic & Temporal Coverage

- **Geographic Granularity**: Village (`shrid_loc_type: village`) and Town/Urban ward (`shrid_loc_type: town`) covering ~600,000 localities across India.
- **Underlying Primary Sources**:
  - Primary Census Abstract (PCA): 2011 Census.
  - Town / Village Directory (VD/TD): 2011 Census.
  - Economic Census (EC): 2013 Economic Census (and historical 1990, 1998, 2005 rounds).
- **Temporal Staleness**:
  - The underlying demographic data is **15 years old** (2011).
  - The establishment and employment data is **13 years old** (2013).
  - *Quality Rating*: Severe staleness across all non-farm business metrics.

---

## 4. Legal Terms & Licensing Conflict (Primary Gate Issue)

- **Licence Name**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
- **Official Licence Link**: [https://devdatalab.org/terms-of-use](https://devdatalab.org/terms-of-use) / [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- **Commercial Use Restriction**:
  - CC BY-NC-SA 4.0 strictly prohibits any commercial exploitation or use within a commercial product.
  - While ArthLens is currently developed as a non-commercial academic and portfolio project, the project charter (Handbook Part 0.1) explicitly defines it as a **"possible startup foundation"**.
  - Embedding a dataset licensed under CC BY-NC-SA 4.0 creates an immediate legal barrier for any future commercialization or dual-licensing spin-off without negotiating an expensive proprietary commercial license directly from Development Data Lab.

---

## 5. Architectural Alignment & Resolution Policy

Pursuant to **Handbook Section 7.4 (Resolution Policy)**:
> *"State and district analysis is expected to be supported. Village-level population and non-farm establishments may be available via SHRUG but are stale. No verified public source of village-level sales, prices or consumption was found. Any figure at that level is ESTIMATED (method registered) or refused. The Atlas shows two tiers: navigable and analysable."*

For the initial MVP:
1. Sub-district (Tehsil) and District population from **DS-05 (LGD / Census 2011)** provides a legally unencumbered, open-access foundation.
2. Micro-level competitor establishment counts are derived directly from **DS-04 (OpenStreetMap)** rather than 2013 Economic Census figures.

---

## 6. Decision Gate

- **Decision**: **`DEFERRED / CONDITIONAL NO-GO (Deferred from Initial MVP)`**
- **Justification**:
  - Severe commercial licensing restriction (CC BY-NC-SA 4.0) conflicts with potential startup foundation.
  - 2013 Economic Census data is too stale to represent 2026 micro-enterprise competition.
  - Eliminating SHRUG from the critical path simplifies Phase 2 ingestion without compromising Loop A, B, or C feasibility workflows.
- **Affected Features**:
  - Village-level non-farm establishment density is deferred to R1/future research. Initial MVP operates at Sub-District and District resolution with OSM point overlays.
