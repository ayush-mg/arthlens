# Phase 0 Checklist: Research, Validation & Setup

> **Current Phase**: Phase 0 (Weeks 1–2 of Handbook Build Schedule)  
> **Authoritative Specification**: [ArthLens Build Handbook](ArthLens_Build_Handbook.pdf) (Part 13.1)  
> **Core Rule**: Do not start Phase 1 (Domain, Ledger, Auth) until all Phase 0 acceptance criteria are satisfied. Tasks designated as **Human Verification Required** must be verified and signed off by a human developer—never self-approved by the AI assistant.

---

## Task Matrix Overview

| Task ID | Task Description | Owner | Execution Type | Acceptance Criteria | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0-1** | Verify each source in the register (Part 7); write `docs/data-sources/*.md` with licence and GO/NO-GO | A + B (human) | 🧑 **Human Required** (AI can format templates) | Every MVP source (DS-01 through DS-09) has a live-verified file with licence terms and explicit GO/NO-GO sign-off. | `NOT STARTED` |
| **P0-2** | Fetch PMFME, PMEGP, PM-MUDRA official guidelines; hash; extract parameters by hand | B (human) | 🧑 **Human Required** (AI can review schema) | PDF hashes (SHA-256) and exact parameter tables extracted with page references into canonical [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md). No secondary blog figures. | `NOT STARTED` |
| **P0-3** | Competitor checks (ONDC, Udyam, MSME Sampark, two deep-research agents); name availability check for ArthLens | A | 🤖 **AI-Assisted** + 🧑 Human Sign-off | Competitor matrix updated with empirical evidence and functional boundaries; name search documented. | `PENDING` |
| **P0-4** | Choose pilot district by the go/no-go gate (Part 7.3); choose two business templates and identify parameter sources | A + B | 🧑 **Human Required** (AI can extract OSM stats) | Written decision with evidence satisfying the road network, POI count, and population resolution criteria. | `NOT STARTED` |
| **P0-5** | Write ledger invariants as tests (Part 4.7) and author the benchmark task format (roughly 60–100 tasks) | A | 🤖 **AI-Assisted** (AI can draft test suite) | Failing unit and property-based test suite committed to git before Phase 1 implementation begins. | `IN PROGRESS` |
| **P0-6** | Confirm hosting limits (Part 14) and LLM provider terms | B | 🤖 **AI-Assisted** + 🧑 Human Decision | All hosting and LLM questions resolved or explicitly listed in [`docs/open-questions.md`](open-questions.md). | `PENDING` |

---

## Detailed Task Work Breakdown

### Task P0-1: Data Source Verification Register
- **Goal**: Verify every public data source candidate before writing ingestion pipelines.
- **Responsibility**: Developers A + B (Human verification required).
- **Canonical Register to Inspect**:
  1. [ ] **DS-01**: `data.gov.in` (`docs/data-sources/ds-01-data-gov-in.md`)
  2. [ ] **DS-02**: `RBI DBIE` (`docs/data-sources/ds-02-rbi-dbie.md`)
  3. [ ] **DS-03**: `SHRUG` (`docs/data-sources/ds-03-shrug.md`)
  4. [ ] **DS-04**: `OpenStreetMap` (`docs/data-sources/ds-04-osm.md`)
  5. [ ] **DS-05**: `Census 2011 / LGD crosswalk` (`docs/data-sources/ds-05-lgd-crosswalk.md`)
  6. [ ] **DS-06**: `NSS / HCES` (`docs/data-sources/ds-06-nss-consumption.md`)
  7. [ ] **DS-07**: `Udyam statistics` (`docs/data-sources/ds-07-udyam.md`)
  8. [ ] **DS-08**: `Government scheme guidelines` (`docs/data-sources/ds-08-schemes.md`)
  9. [ ] **DS-09**: `Administrative boundaries` (`docs/data-sources/ds-09-administrative-boundaries.md`)
- **Status**: `NOT STARTED`

---

### Task P0-2: Official Policy Scheme Guidelines & Parameter Extraction
- **Goal**: Establish the verified ground truth for government loan and subsidy schemes.
- **Responsibility**: Developer B (Human verification required).
- **Rules**:
  - *Never copy numbers from summary articles, news blogs, or handbook illustrative text.*
  - Directly download official PDF guidelines from government ministry portals.
  - Compute and record SHA-256 checksums of each downloaded document.
- **Sub-tasks**:
  1. [ ] Download official PMFME operational guidelines, calculate SHA-256, record URL and date.
  2. [ ] Download official PMEGP operational guidelines, calculate SHA-256, record URL and date.
  3. [ ] Download official PM-MUDRA guidelines, calculate SHA-256, record URL and date.
  4. [ ] Extract subsidy rates, ceilings, applicant contribution, moratorium rules, and subsidy release mechanisms with page/section citations.
  5. [ ] Commit findings exclusively to canonical [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md).
- **Status**: `NOT STARTED`

---

### Task P0-3: Competitor & Precedent Analysis, Name Verification
- **Goal**: Clarify ArthLens's exact positioning and verify name availability.
- **Responsibility**: Developer A (AI-assisted research, human review).
- **Sub-tasks**:
  1. [ ] Review public capabilities of ONDC (Open Network for Digital Commerce) retail tools.
  2. [ ] Review MSME Sampark and Udyam portal capabilities to confirm lack of financial modeling linkage.
  3. [ ] Check two general deep-research agents to benchmark single-pass LLM limitations.
  4. [ ] Check trademark registry and software repositories (PyPI, npm, GitHub) for "ArthLens".
  5. [ ] Update Section 1.5 competitor table with primary evidence.
- **Status**: `PENDING`

---

### Task P0-4: Pilot District Selection via Go/No-Go Gate
- **Goal**: Confirm or replace the default candidate district (Prayagraj, Uttar Pradesh).
- **Responsibility**: Developers A + B (Human review required).
- **Gate Criteria (Handbook Section 7.3)**:
  1. [ ] **Road Network & POIs**: Usable road network and categorized POI points verified in OSM for the district.
  2. [ ] **Population Data**: Population counts available at sub-district or village level with a documented `as_of` date.
  3. [ ] **Policy Schemes**: At least three official schemes fetched and verified in Task P0-2.
  4. [ ] **Business Templates**: Confirm two target micro-enterprise templates (Retail Grocery and Food-Processing / Tiffin).
  5. [ ] Write formal decision record with gate evidence in `docs/DECISIONS.md`.
- **Status**: `NOT STARTED`

---

### Task P0-5: Ledger Invariants and Benchmark Task Format
- **Goal**: Build the correctness-first testing foundation before writing any production code.
- **Responsibility**: Developer A (AI can draft test code, human approves).
- **Sub-tasks**:
  1. [ ] Author Hypothesis property-based tests in `tests/property/` asserting:
     - Evidence floor never strengthens across derivation ($\min(\text{parents})$).
     - Geographic resolution never refines without registered downscaling (`popweight_v1`).
     - Ledger graph rejects cycles (strict DAG).
     - UNQUANTIFIED uncertainty is contagious across calculations.
  2. [ ] Author unit tests in `tests/unit/` for specifications V1 through V9.
  3. [ ] Author the benchmark task schema and authoring template targeting roughly **60–100 tasks** across Loops A, B, and C with gold labels (Part 12.2).
  4. [ ] Verify that tests run and fail as expected (TDD red stage).
- **Status**: `IN PROGRESS`

---

### Task P0-6: Hosting Limits, Infrastructure & LLM Provider Terms
- **Goal**: Lock down free-tier boundaries and resolve architecture questions.
- **Responsibility**: Developer B (AI-assisted research, human decision).
- **Acceptance Rule (Handbook Part 13.1)**: Questions must be resolved or explicitly listed in [`docs/open-questions.md`](open-questions.md).
- **Sub-tasks**:
  1. [ ] **Implementation-Blocking Items**:
     - Verify local Docker Compose setup with PostgreSQL 16 + PostGIS 3.4.
     - Verify Python environment compatibility: resolve Python 3.14.5 (host) vs. Python 3.12 (handbook spec) dependency wheel availability.
     - Validate `ILLMClient` structured schema test fixture (`FakeLLMClient`).
  2. [ ] **Deployment Items (Can Wait Until Phase 7)**:
     - Document PostGIS extension limits on managed Postgres providers (Neon/Supabase/Render).
     - Measure container cold-start delay and background worker process limits.
  3. [ ] **Cost Governance**:
     - Confirm `MAX_COST_USD_PER_RUN = 0.25` as a configurable, unmeasured starting hypothesis enforced in code via `BudgetEnforcementDecorator`.
- **Status**: `PENDING`
