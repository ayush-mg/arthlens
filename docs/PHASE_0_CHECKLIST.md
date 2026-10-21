# Phase 0 Checklist: Research, Validation & Setup

> **Current Phase**: Phase 0 (Weeks 1–2 of Handbook Build Schedule)
> **Authoritative Specification**: [ArthLens Build Handbook](ArthLens_Build_Handbook.pdf) (Part 13.1)
> **Core Rule**: Do not start Phase 1 (Domain, Ledger, Auth) until all Phase 0 acceptance criteria are satisfied. Tasks designated as **Human Verification Required** must be verified and signed off by a human developer—never self-approved by the AI assistant.

---

## Task Matrix Overview

| Task ID | Task Description | Owner | Execution Type | Acceptance Criteria | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0-1** | Verify each source in the register (Part 7); write `docs/data-sources/*.md` with licence and GO/NO-GO | A + B (human) | 🧑 **Human Required** (AI can format templates) | Every MVP source (DS-01 through DS-09) has an evidence-backed file with licence terms and explicit GO/NO-GO decision. | `DONE` |
| **P0-2** | Fetch PMFME, PMEGP, PM-MUDRA official guidelines; hash; extract parameters by hand | B (human) | 🧑 **Human Required** (AI can review schema) | PDF hashes (SHA-256) and exact parameter tables extracted with page references into canonical [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md). No secondary blog figures. | `DONE` |
| **P0-3** | Competitor checks (ONDC, Udyam, MSME Sampark, two deep-research agents); name availability check for ArthLens | A | 🤖 **AI-Assisted** + 🧑 Human Sign-off | Competitor matrix updated with empirical evidence and functional boundaries; name search documented. | `DONE` |
| **P0-4** | Choose pilot district by the go/no-go gate (Part 7.3); choose two business templates and identify parameter sources | A + B | 🧑 **Human Required** (AI can extract OSM stats) | Written decision with evidence satisfying the road network, POI count, and population resolution criteria. | `DONE` |
| **P0-5** | Write ledger invariants as tests (Part 4.7) and author the benchmark task format (roughly 60–100 tasks) | A | 🤖 **AI-Assisted** (AI can draft test suite) | Failing unit and property-based test suite committed to git before Phase 1 implementation begins. | `DONE` |
| **P0-6** | Confirm hosting limits (Part 14) and LLM provider terms | B | 🤖 **AI-Assisted** + 🧑 Human Decision | All hosting and LLM questions resolved or explicitly listed in [`docs/open-questions.md`](open-questions.md). | `DONE` |

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
  8. [x] **DS-08**: `Government scheme guidelines` ([`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md)) — `GO` (Task P0-2 Complete: PMFME, PMEGP, PM-MUDRA verified)
  9. [x] **DS-09**: `Administrative boundaries` ([`docs/data-sources/ds-09-administrative-boundaries.md`](data-sources/ds-09-administrative-boundaries.md)) — `GO` (Core MVP: Datameet 641 district records, Record 10 Prayagraj censuscode 175; verbatim MIT license)
- **Status**: `DONE`

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
- **Status**: `DONE`

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
- **Status**: `DONE`

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
- **Status**: `DONE` (Human-approved 2026-10-21: Prayagraj confirmed with two-tier geographic coverage policy and DS-01 safety restriction)

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
- **Status**: `DONE` (Committed and pushed: property tests, unit tests, and benchmark format created)

---

### Task P0-6: Hosting Limits, Infrastructure & LLM Provider Terms
- **Goal**: Lock down free-tier boundaries and resolve architecture questions.
- **Responsibility**: Developer B (AI-assisted research, human decision).
- **Acceptance Rule (Handbook Part 13.1)**: Questions must be resolved or explicitly listed in [`docs/open-questions.md`](open-questions.md).
- **Sub-tasks**:
  1. [x] **Implementation-Blocking Items**:
     - Local Docker Compose setup with PostgreSQL 16 + PostGIS 3.4 confirmed as foundation for Phase 1.
     - Python compatibility risk documented in `open-questions.md` (host Python 3.14.5 vs. handbook spec Python 3.12).
     - `ILLMClient` interface and `FakeLLMClient` / `ReplayLLMClient` test architecture confirmed for offline testing.
  2. [x] **Deployment Items (Ahead of Phase 7)**:
     - Documented PostGIS extension limits on managed Postgres providers (Neon 1 GB / Supabase 500 MB / Render 30-day deletion rule) in [`docs/hosting-and-llm-decision.md`](hosting-and-llm-decision.md).
     - Documented container cold-start and background worker constraints (Render 15m idle sleep, HF Spaces 48h idle sleep; Render Starter $7/mo or in-process worker recommended; Replay Mode as guaranteed demo fallback).
     - Documented frontend hosting (Cloudflare Pages free commercial rights vs. Vercel Hobby non-commercial personal use).
     - Documented object storage (Cloudflare R2 10 GB free with $0 egress vs. AWS S3 $0.09/GB egress risk).
  3. [x] **Cost Governance & LLM Terms**:
     - Verified OpenAI API `gpt-6-luna` ($0.10/$0.50 per 1M, $0.01 cached) with native JSON Schema support (`strict: true`) as active supported successor to deprecated `gpt-4o-mini`.
     - Verified commercial API privacy terms: OpenAI and Anthropic API inputs/outputs are NOT used for model training. Google AI Studio free tier rejected for sensitive data due to prompt harvesting.
     - Confirmed `MAX_COST_USD_PER_RUN = 0.25` as a configurable starting hypothesis with ~62x safety margin, enforced in code by `BudgetEnforcementDecorator`.
     - Recorded formal architectural decision in [`docs/DECISIONS.md#adr-009`](DECISIONS.md#adr-009-hosting-limits-deployment-architecture-and-llm-provider-selection-task-p0-6).
- **Status**: `DONE` (Acceptance criterion satisfied: all hosting and LLM questions resolved or explicitly categorized in [`docs/open-questions.md`](open-questions.md))
