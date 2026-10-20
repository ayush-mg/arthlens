# Data Source: NSS / Household Consumption Expenditure Survey (HCES) (DS-06)

> **Verification Status**: `DEFERRED (R1)` (Deferred from Initial MVP Foundation)
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (Part 7.1, 7.4, 13.1)
> **Product Scope**: ArthLens is the **final, deployable, noncommercial academic and portfolio product**. Its intended scope is **nationwide across India**.
> **MVP Essentiality**: **NON-ESSENTIAL / DEFERRED**. Initially proposed as an empirical spending benchmark for spatial downscaling (`popweight_v1`). Deferred due to the absence of official district-level direct estimates in published reports.

---

## 1. Identity & Publisher

- **Source ID**: `DS-06`
- **Official Name**: Household Consumption Expenditure Survey (HCES: 2022-23 and 2023-24) / National Sample Survey (NSS)
- **Publishing Authority**: National Sample Survey Office (NSSO), Ministry of Statistics and Programme Implementation (MoSPI), Government of India
- **Official Portal**: [https://www.mospi.gov.in](https://www.mospi.gov.in)
- **Microdata Portal**: [https://microdata.gov.in](https://microdata.gov.in)

---

## 2. Access Method & Data Structure

- **Access Protocols**:
  - Official Summary Factsheets & Reports: Downloadable PDF tables.
  - Raw Unit-Level Microdata: Downloadable via MoSPI Microdata Portal (fixed-width text/CSV format requiring survey sampling weights).
- **Authentication**: User registration required for unit-level microdata access.

---

## 3. Geographic Granularity Deficiency & Resolution Findings

- **Published Reporting Level**:
  - Official MoSPI HCES reports provide Monthly Per Capita Consumption Expenditure (MPCE) breakdowns **strictly at the All-India and State / Union Territory levels** (segregated by Rural and Urban sectors).
  - **No official direct sample estimates are published for all 780+ districts**. The NSS survey sampling frame is statistically powered for state and national aggregates, not granular district or tehsil tiers.
- **Experimental Small Area Estimation (SAE)**:
  - While MoSPI pilot committees have explored model-based district MPCE estimates (e.g. Fay-Herriot small area models for select states), these remain experimental research outputs rather than standardized, continuously published official datasets.

---

## 4. Legal Terms & Attribution

- **Licence Terms**: Government of India Open Data / MoSPI Microdata Dissemination Policy. Permitted for academic and policy analysis with mandatory attribution.
- **Attribution String**:
  > *"Household Consumption Expenditure Survey (HCES), National Sample Survey Office, Ministry of Statistics and Programme Implementation (MoSPI), Government of India."*

---

## 5. Architectural Alignment with ArthLens MVP

Under the ArthLens **Evidence Gating** model:
1. The platform strictly prohibits presenting estimated or downscaled numbers as observed empirical facts (Handbook Section 0.2, Rule 1).
2. For **MVP Loop B (Spatial Demand Allocation)**:
   - Demand allocation models (Nearest and Huff allocators) operate on local catchment population counts from **DS-05 (Census/LGD)**.
   - Average transaction size and customer spending propensity are entered as **`USER_ASSUMED`** parameters or explored as **`SCENARIO`** bounds within the Scenario Laboratory.
   - This approach is fully supported by Handbook Section 8.4 and avoids fabricating unverified village-level consumption figures.

---

## 6. Decision Gate

- **Decision**: **`DEFERRED (R1)`**
- **Justification**:
  - Absence of standardized, authoritative district-level consumption tables in primary MoSPI releases.
  - Avoids introducing unverified microdata downscaling models into the Phase 0 critical path.
  - Spatial demand allocation in the MVP operates transparently using catchment population and user-controlled ticket sizes.
- **Affected Features**:
  - Automated empirical district per-capita spending benchmarks are deferred to R1.
