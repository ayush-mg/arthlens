# Phase 0 Checklist: Research, Validation & Setup

> **Current Phase**: Phase 0 acceptance evidence remains partially open; later implementation phases have started, but that does not waive Phase 0 gates.
> **Authoritative Specification**: [ArthLens Build Handbook](ArthLens_Build_Handbook.pdf) (Part 13.1)
> **Status Authority**: The evidence-based [Master Execution Tracker](MASTER_EXECUTION_TRACKER.md) is authoritative when task status conflicts with this historical checklist. Tasks designated as **Human Verification Required** must be verified and signed off by a human developer—never self-approved by the AI assistant.

---

## Task Matrix Overview

| Task ID | Task Description | Owner | Execution Type | Acceptance Criteria | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0-1** | Verify each source in the register (Part 7); write `docs/data-sources/*.md` with licence and GO/NO-GO | A + B (human) | 🧑 **Human Required** (AI can format templates) | Every MVP source has a scoped, evidence-backed gate; no unreviewed source is promoted to production use. | `IN PROGRESS` (DS-01 pending; source approvals and scopes need reconciliation) |
| **P0-2** | Fetch PMFME, PMEGP, PM-MUDRA official guidelines; hash; extract parameters by hand | B (human) | 🧑 **Human Required** (AI can review schema) | PDF hashes and extracted tables exist; a qualified human confirms parameters, current effective dates, and mechanisms before rules or finance claims are approved. | `BLOCKED` (independent human validation/sign-off outstanding) |
| **P0-3** | Competitor checks (ONDC, Udyam, MSME Sampark, two deep-research agents); name availability check for ArthLens | A | 🤖 **AI-Assisted** + 🧑 Human Sign-off | Competitor matrix and name-search findings are documented; human review is required before public market or name-availability claims. | `IN PROGRESS` (research documented; human review outstanding) |
| **P0-4** | Choose pilot district by the go/no-go gate (Part 7.3); choose two business templates and identify parameter sources | A + B | 🧑 **Human Required** (AI can extract OSM stats) | Recorded Prayagraj decision is reconciled with current source gates and required evidence. | `IN PROGRESS` (decision recorded; prerequisite source gates remain open) |
| **P0-5** | Write ledger invariants as tests (Part 4.7) and author the benchmark task format (roughly 60–100 tasks) | A | 🤖 **AI-Assisted** (AI can draft test suite) | Failing unit and property-based test suite committed to git before Phase 1 implementation begins; benchmark schema & dev tasks completed; 60–100 gold tasks in progress. | `IN PROGRESS (Human Annotation Required)` |
| **P0-6** | Confirm hosting limits (Part 14) and LLM provider terms | B | 🤖 **AI-Assisted** + 🧑 Human Decision | Current official provider terms, quotas, deployment support, and pricing are verified; hosting/provider selection is human-authorized. | `BLOCKED` (notes exist; current verification and authorization outstanding) |

---

## Detailed Task Work Breakdown

### Task P0-1: Data Source Verification Register
- **Goal**: Verify every public data source candidate before writing ingestion pipelines.
- **Responsibility**: Developers A + B (Human verification required for final GO sign-off).
- **Canonical Register Audited**:
  1. [x] **DS-01**: `data.gov.in` ([`docs/data-sources/ds-01-data-gov-in.md`](data-sources/ds-01-data-gov-in.md)) — `PENDING` (Live audit complete: 16,080 records across 26 states; GODL-India identified; price unit caveat documented)
  2. [x] **DS-02**: `RBI DBIE` ([`docs/data-sources/ds-02-rbi-dbie.md`](data-sources/ds-02-rbi-dbie.md)) — `DEFERRED (R1)` (Lacks public REST API; non-essential for MVP calculations)
  3. [x] **DS-03**: `SHRUG` ([`docs/data-sources/ds-03-shrug.md`](data-sources/ds-03-shrug.md)) — `DEFERRED / CONDITIONAL NO-GO` (CC BY-NC-SA 4.0 commercial conflict; 2013 EC staleness)
  4. [x] **DS-04**: `OpenStreetMap` ([`docs/data-sources/ds-04-osm.md`](data-sources/ds-04-osm.md)) — `GO` (Core MVP: Live Prayagraj sample with 1,253 nodes / 202 ways; verbatim ODbL terms; completeness caveat)
  5. [x] **DS-05**: `Census 2011 / LGD crosswalk` ([`docs/data-sources/ds-05-lgd-crosswalk.md`](data-sources/ds-05-lgd-crosswalk.md)) — `GO` (Core MVP: Prayagraj District 175 PCA sample of 5,954,391 pop; verbatim GODL terms)
  6. [x] **DS-06**: `NSS / HCES` ([`docs/data-sources/ds-06-nss-consumption.md`](data-sources/ds-06-nss-consumption.md)) — `DEFERRED (R1)` (MoSPI publishes state-level only; no official district estimates)
  7. [x] **DS-07**: `Udyam statistics` ([`docs/data-sources/ds-07-udyam.md`](data-sources/ds-07-udyam.md)) — `NO-GO (Spatial) / DEFERRED (Macro)` (Private address records; OSM POIs used for spatial competitors)
  8. [x] **DS-08**: `Government scheme guidelines` ([`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md)) — Official documents, hashes, and extracted citations are present; operational rule approval is `BLOCKED` pending independent human verification (P0-2).
  9. [x] **DS-09**: `Administrative boundaries` ([`docs/data-sources/ds-09-administrative-boundaries.md`](data-sources/ds-09-administrative-boundaries.md)) — Approval is limited to the documented Prayagraj pilot; nationwide modern and subdistrict polygons remain source-gated.
- **Status**: `IN PROGRESS` (source documentation and preliminary audits exist; source-specific human approvals are not complete)

---

### Task P0-2: Official Policy Scheme Guidelines & Parameter Extraction
- **Goal**: Establish the verified ground truth for government loan and subsidy schemes.
- **Responsibility**: Developer B (Human verification required).
- **Rules**:
  - *Never copy numbers from summary articles, news blogs, or handbook illustrative text.*
  - Directly download official PDF guidelines from government ministry portals.
  - Compute and record SHA-256 checksums of each downloaded document.
- **Sub-tasks**:
  1. [x] Download official PMFME operational guidelines, calculate SHA-256, record URL and date.
  2. [x] Download official PMEGP operational guidelines, calculate SHA-256, record URL and date.
  3. [x] Download official PM-MUDRA guidelines, calculate SHA-256, record URL and date.
  4. [x] Extract subsidy rates, ceilings, applicant contribution, moratorium rules, and subsidy release mechanisms with page/section citations.
  5. [x] Commit findings to canonical [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md), [`docs/schemes/source_register.md`](schemes/source_register.md), and [`docs/schemes/parameter_register.md`](schemes/parameter_register.md).
- **Status**: `BLOCKED` (official PDFs, hashes, and extracted parameters exist; independent human parameter/effective-date/mechanism validation is outstanding)

---

### Task P0-3: Competitor & Precedent Analysis, Name Verification
- **Goal**: Clarify ArthLens's exact positioning and verify name availability.
- **Responsibility**: Developer A (AI-assisted research, human review).
- **Sub-tasks**:
  1. [x] Review public capabilities of ONDC (Open Network for Digital Commerce) retail tools.
  2. [x] Review MSME Sampark and Udyam portal capabilities to confirm lack of financial modeling linkage.
  3. [x] Check two general deep-research agents to benchmark single-pass LLM limitations (OpenAI Deep Research / Perplexity, Stanford STORM).
  4. [x] Check trademark registry, corporate namespace (Arthlens Technologies Pvt Ltd), and software repositories (PyPI, npm, GitHub) for "ArthLens" ([`docs/name-search.md`](name-search.md)).
  5. [x] Update Section 1.5 competitor table with primary evidence and functional boundaries ([`docs/competitor-analysis.md`](competitor-analysis.md)).
- **Status**: `IN PROGRESS` (research artifacts exist; human review remains required before public claims)

---

### Task P0-4: Pilot District Selection via Go/No-Go Gate
- **Goal**: Confirm or replace the default candidate district (Prayagraj, Uttar Pradesh).
- **Responsibility**: Developers A + B (Human review required).
- **Gate Criteria (Handbook Section 7.3)**:
  1. [x] **Road Network & POIs**: Usable road network and categorized POI points verified in OSM for the district ([`docs/data-sources/ds-04-osm.md`](data-sources/ds-04-osm.md)).
  2. [x] **Population Data**: Population counts available at sub-district or village level with a documented `as_of` date ([`docs/data-sources/ds-05-lgd-crosswalk.md`](data-sources/ds-05-lgd-crosswalk.md)).
  3. [x] **Policy Schemes**: At least three official schemes fetched and verified in Task P0-2 ([`docs/schemes/source_register.md`](schemes/source_register.md)).
  4. [x] **Business Templates**: Confirm two target micro-enterprise templates: Retail Grocery and Food-Processing / Tiffin ([`docs/pilot-district-decision.md`](pilot-district-decision.md)).
  5. [x] Write formal decision record with gate evidence in [`docs/DECISIONS.md`](DECISIONS.md#adr-008-pilot-district-selection-prayagraj-up-and-business-template-selection).
- **Status**: `IN PROGRESS` (a Prayagraj decision is recorded as human-approved on 2026-10-21; current source-gate reconciliation remains outstanding)

---

### Task P0-5: Ledger Invariants and Benchmark Task Format
- **Goal**: Build the correctness-first testing foundation before writing any production code.
- **Responsibility**: Developer A (AI can draft test code, human approves).
- **Sub-tasks**:
  1. [x] Author Hypothesis property-based tests in `tests/property/` asserting:
     - Evidence floor never strengthens across derivation ($\min(\text{parents})$).
     - Geographic resolution never refines without registered downscaling (`popweight_v1`).
     - Ledger graph rejects cycles (strict DAG).
     - UNQUANTIFIED uncertainty is contagious across calculations.
  2. [x] Author unit tests in `tests/unit/` for specifications V1 through V9.
  3. [ ] Author the benchmark task schema and authoring template targeting roughly **60–100 tasks** across Loops A, B, and C with gold labels (Part 12.2).
     - *Status*: Schema (`benchmark/task_schema.json`) and 6 dev sample tasks (`benchmark/tasks/dev/sample_tasks.json`) authored and schema-validated. Full 60–100 human-labelled gold benchmark suite remains IN PROGRESS awaiting human domain-expert annotation (non-fabricated).
  4. [x] Verify that tests run and fail as expected (TDD red stage).
- **Status**: `IN PROGRESS` (Unit tests, property tests, and benchmark task schema authored; human annotation of 60–100 benchmark tasks in progress)

---

### Task P0-6: Hosting Limits, Infrastructure & LLM Provider Terms
- **Goal**: Lock down free-tier boundaries and resolve architecture questions.
- **Responsibility**: Developer B (AI-assisted research, human decision).
- **Acceptance Rule (Handbook Part 13.1)**: Questions must be resolved or explicitly listed in [`docs/open-questions.md`](open-questions.md).
- **Sub-tasks**:
  1. [x] **Implementation-Blocking Items**:
     - Local Docker Compose setup with PostgreSQL 16 + PostGIS 3.4 is configured for local development; provider limits and deployment suitability are not established.
     - Python compatibility decision is documented; it does not resolve vendor, deployment, or procurement approval.
     - `ILLMClient` and local test-double architecture exist; this does not establish a production LLM provider or end-to-end replay readiness.
  2. [ ] **Deployment Items (Ahead of Phase 7)**:
     - Historical provider/deployment notes exist in [`docs/hosting-and-llm-decision.md`](hosting-and-llm-decision.md); their prices, quotas, terms, and limits are not accepted as current.
     - No provider is selected or authorized; no deployment support or production fallback is verified.
  3. [ ] **Cost Governance & LLM Terms**:
     - Earlier model, price, privacy, quota, and cost-safety claims are not current procurement evidence and must not be relied on without rechecking primary provider terms.
     - Configuration and test interfaces do not establish end-to-end budget enforcement or measured safety margins; see P4-3 and P6-3 in the Master Execution Tracker.
     - [`docs/DECISIONS.md#adr-009`](DECISIONS.md#adr-009-hosting-limits-deployment-architecture-and-llm-provider-selection-task-p0-6) records prior research/architecture, not current vendor verification or authorization.
- **Status**: `BLOCKED` (open questions are documented, but current official terms and human authorization are not established)
