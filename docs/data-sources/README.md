# Data Sources Documentation & Verification Standard

> **Crucial Rule**: **No dataset is considered verified merely because it is listed in the ArthLens Build Handbook.**
> Every proposed source must undergo rigorous primary human inspection during Phase 0 before an ingestion adapter may be written. Unverified data must never enter the codebase.
> **Authoritative Specification**: [ArthLens Build Handbook](../ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026)

---

## 1. Purpose of This Directory

This directory (`docs/data-sources/`) establishes the documentation standards and verification register for all external datasets evaluated for ArthLens.

Under the ArthLens **Evidence Gating** model:
- The system strictly distinguishes between what is observed, what is an official rule, what is user-assumed, and what is estimated.
- If a dataset lacks sub-district granularity, the platform will **not** invent numbers or claim village-level certainty.
- If a source fails legal licensing or reliability checks, it is marked `NO-GO`, and either replaced with a verified alternative or its dependent feature is removed from scope.

---

## 2. Permitted Inputs and Evidence Classification

### 2.1 Evidence Kind Is Quantity-Specific, Not Dataset-Wide
It is incorrect to assume that every ingested dataset automatically produces quantities of kind `OBSERVED`. The classification depends strictly on what the quantity represents:
- **`OBSERVED`**: Real-world empirical measurements and published statistics (e.g. district population counts from official census tables, quarterly bank deposit totals from RBI DBIE).
- **`POLICY_RULE`**: Official government statutory guidelines, eligibility criteria, subsidy percentages, and parameter caps (e.g. PMFME subsidy rules extracted from official ministry PDFs).
- **`USER_ASSUMED`**: Facts, capital limits, and constraints provided directly by the entrepreneur (e.g. planned equity capital, target business sector, candidate site selections).
- **`ESTIMATED`**: Values derived through registered approximation methods where direct empirical counts do not exist (e.g. sub-district demand computed via `popweight_v1` spatial downscaling).
- **`SCENARIO`**: Exploratory what-if parameters and simulation bounds (e.g. assumed customer capture rates, varying raw-material price bounds).

### 2.2 User Inputs and Scenarios Are First-Class Inputs
Verified external public data is **not** the only permitted input to ArthLens. User inputs (`USER_ASSUMED`) and explicitly labelled scenarios (`SCENARIO`) are fully valid and necessary to run financial feasibility models and sensitivity analyses. However, the system strictly enforces that user assumptions and scenarios must **never** be passed off or displayed as observed empirical facts.

### 2.3 Verification Fixtures vs. Production Evidence
During development, testing, and offline evaluation, local static fixtures and mock adapters may be used to validate pipeline mechanics. These test fixtures must be explicitly segregated and **must never be misrepresented as verified production evidence**.

---

## 3. Source Lifecycle and Verification Status

Each candidate source progresses through these explicit states:

```
[PROPOSED] ──> [UNDER VERIFICATION] ──> [GO]    (Adapter implemented in Phase 2)
                                      └──> [NO-GO] (Feature cut or alternative sought)
```

- **`PROPOSED`**: Mentioned in handbook or research; no live inspection performed yet.
- **`UNDER VERIFICATION`**: Primary human inspection underway (API tested, schema recorded, licensing examined).
- **`GO`**: A human reviewer verified the live endpoint or bulk file, recorded sample rows, confirmed legal licence terms, and signed off with date.
- **`NO-GO`**: The source failed verification (e.g. restrictive license, dead API, extreme staleness, or missing identifiers). Dependent features must be cut or downgraded.

---

## 4. Mandatory Specification Template

For each dataset, a dedicated markdown file must be created at `docs/data-sources/<source-id>.md` (e.g., `docs/data-sources/ds-01-data-gov-in.md`) adhering to this exact schema:

```markdown
# Data Source: [Source Name] ([Canonical ID])

## 1. Identity & Publisher
- **Source ID**: `DS-XX`
- **Official Name**: [Full dataset title]
- **Publisher / Department**: [Publishing ministry, agency, or organisation]
- **Official Portal URL**: [Link to landing page]
- **API Documentation / Direct Download URL**: [Link to developer docs or bulk data]

## 2. Access Method & Authentication
- **Access Protocol**: [REST API (JSON/CSV) | Bulk File Download (ZIP/XLSX/GeoJSON) | Scraping strictly prohibited]
- **Authentication**: [None / Public | API Key required | Login required]
- **Rate Limits & Constraints**: [e.g., 100 requests/minute, max file size]
- **Fallback Plan**: [Path to cached snapshot stored in S3/R2 storage for offline demo]

## 3. Geographic & Temporal Coverage
- **Geographic Granularity**: [National (0) | State (1) | District (2) | Sub-district/Tehsil (3) | Village/Ward (4) | Point (5)]
- **Identifier Scheme**: [LGD Code | Census 2011 Code | Pin Code | Custom Strings]
- **Crosswalk Requirement**: [Specify if a mapping table is needed to link to official LGD codes]
- **Temporal Coverage**: [Start year/period to end year/period]
- **As-Of Date**: [Latest reference date represented in the data]
- **Update Frequency**: [Daily | Monthly | Quarterly | Annual | Decennial / Static]
- **Staleness Threshold (`max_age_days`)**: [Number of days before the STALE quality flag is applied]

## 4. Legal Terms, Licence & Attribution
- **Licence Name**: [e.g., Government Open Data License (GODL) India | ODbL 1.0 | CC-BY 4.0 | Custom]
- **Verbatim Licence Text Link**: [Direct URL to official licence terms]
- **Commercial & Non-Commercial Usage Terms**: [Explicit statement on whether non-academic or commercial evaluation is permitted]
- **Mandatory Attribution String**: [Exact citation string to display in ArthLens UI and exports]

## 5. Live Inspection & Verification Findings
*(Must be performed by a human reviewer on a recorded date)*
- **Inspection Date**: YYYY-MM-DD
- **Inspector**: [Human Name / Role]
- **Endpoint / Resource ID Tested**: [Exact string or URL tested]
- **Response Row Count**: [e.g., 750 districts, 12,000 rows]
- **Schema & Key Fields**:
  | Field Name | Data Type | Units / Meaning | Present for Pilot District? |
  | :--- | :--- | :--- | :--- |
  | `...` | `...` | `...` | `Yes / No` |
- **Sample Data**:
  ```json
  [ { "example": "value" } ]
  ```
- **Observed Data Quality Issues**: [Missing fields, duplicate rows, unit inconsistencies, or anomalies]

## 6. Intended Application in ArthLens
- **Workflows Involved**: [Loop A | Loop B | Loop C]
- **Dependent Engines / Tools**: [e.g., `fetch_economic_indicator`, `compute_catchment`, `popweight_v1`]
- **Resulting Quantity Definition Keys**: [e.g., `population.total`, `credit.outstanding.district`]
- **Evidence Kind**: [OBSERVED for empirical data | POLICY_RULE for official guidelines]

## 7. Decision Gate
- **Decision**: **`[GO | NO-GO | PENDING]`**
- **Justification**: [Clear, evidence-backed justification for inclusion or exclusion]
- **Signed-off By**: [Human reviewer signature / username]
- **Sign-off Date**: YYYY-MM-DD
```

---

## 5. Canonical Register of Candidate Sources (Task P0-1 Audit Status)

*Note: All sources below have undergone consolidated Phase 0 audit pursuant to Handbook Part 7 and Task P0-1 requirements. Core MVP dependencies are distinguished from deferred or restricted candidates.*

### 5.1 Core MVP Dependencies (In-Scope for Initial Implementation)

| Canonical ID | Source Name | Canonical Path | MVP Role & Workflows | Decision / Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **DS-01** | **data.gov.in (OGD)** | [`ds-01-data-gov-in.md`](ds-01-data-gov-in.md) | Loop A: Mandi commodity prices & agricultural indicators | `PENDING` (Audit completed; awaiting price unit sign-off) |
| **DS-04** | **OpenStreetMap** | [`ds-04-osm.md`](ds-04-osm.md) | Loop B: Road networks (Dijkstra catchments) & POI competitor counts | `GO` (Approved with mandatory completeness caveat) |
| **DS-05** | **Census 2011 / LGD crosswalk** | [`ds-05-lgd-crosswalk.md`](ds-05-lgd-crosswalk.md) | Canonical geographic hierarchy, LGD codes & demographic base | `GO` (Approved; frozen fixture eliminates portal downtime) |
| **DS-08** | **Government scheme guidelines** | [`ds-08-schemes.md`](ds-08-schemes.md) | Loop C: PMFME, PMEGP, PM-MUDRA parameter registers & rule trees | `GO` (Task P0-2 Complete; 42 verified parameters extracted) |
| **DS-09** | **Administrative boundaries** | [`ds-09-administrative-boundaries.md`](ds-09-administrative-boundaries.md) | Atlas: MapLibre vector boundaries & PMTiles edge serving | `GO` (Approved; conforms to Survey of India boundary norms) |

### 5.2 Deferred / Scope-Limited Sources (Non-Essential for MVP)

| Canonical ID | Source Name | Canonical Path | Evaluated Role | Decision / Action |
| :--- | :--- | :--- | :--- | :--- |
| **DS-02** | **RBI DBIE** | [`ds-02-rbi-dbie.md`](ds-02-rbi-dbie.md) | District banking credit/deposit ratios | `DEFERRED (R1)` (Non-essential for loan arithmetic; portal lacks REST API) |
| **DS-03** | **SHRUG (DDL)** | [`ds-03-shrug.md`](ds-03-shrug.md) | Village population & non-farm establishments | `DEFERRED / CONDITIONAL NO-GO` (CC BY-NC-SA 4.0 commercial conflict; 2013 EC staleness) |
| **DS-06** | **NSS / HCES** | [`ds-06-nss-consumption.md`](ds-06-nss-consumption.md) | Per-capita consumption spending downscaling | `DEFERRED (R1)` (MoSPI publishes state-level only; no official district estimates) |
| **DS-07** | **Udyam statistics** | [`ds-07-udyam.md`](ds-07-udyam.md) | Local MSME competitor density | `NO-GO (Spatial) / DEFERRED (Macro)` (Private address records; OSM POIs used for spatial competitors) |
