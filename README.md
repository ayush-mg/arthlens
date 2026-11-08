# ArthLens

> **Status: Full Autonomous Implementation Complete (Phases 1 through 7 Verified & Passed)**
>
> *An agentic, evidence-gated economic decision engine for Indian micro-enterprises.*  
> **Authoritative Specification**: [ArthLens Build Handbook](docs/ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026)

---

## 1. What is ArthLens?

**ArthLens** is an open, evidence-governed decision-support platform designed to assist prospective micro-entrepreneurs in India in exploring two foundational questions:
1. **Is this small business idea economically viable?**
2. **Where within a district is the most promising location to set it up?**

Unlike conventional business dashboards that display static charts or generic AI chatbots that guess answers, ArthLens is architected around an **Epistemic Ledger**—a verifiable accounting system for data where **every single number is tagged with its origin, resolution, and certainty level**.

The core design principle of ArthLens is **evidence gating**: the system refuses to present estimates as observed facts, refuses to claim village-level precision when only district averages exist, and mandates that all financial calculations, spatial modeling, and policy eligibility checks are evaluated by deterministic, auditable code rather than large language model (LLM) guesswork.

> **Implementation Status & Scope**:
> - **Phase 1 (Foundations & Core Domains)**: Complete (PASS). Pint units, immutable `Quantity`, verification specifications, PostgreSQL 16 + PostGIS repositories, and RBAC matrix.
> - **Phase 2 (Data Ingestion & Geographic Grounding)**: Complete (PASS). Official pipelines for OpenStreetMap (`DS-04`), LGD/Census 2011 (`DS-05`), Government Schemes (`DS-08`), and Administrative Boundaries (`DS-09`), with 6-state data quality shading (`CURRENT`, `INCOMPLETE`, `STALE`, `ESTIMATED`, `UNAVAILABLE`, `CONTRADICTED`).
> - **Phase 3 (Computational Engine)**: Complete (PASS). Custom Dijkstra road routing, Huff gravity allocation, deterministic loan amortization & cash flows, reproducible Monte Carlo simulations, one-at-a-time sensitivity, and 3-valued Kleene policy evaluation.
> - **Phase 4 (Agent Orchestration & Gemini Integration)**: Complete (PASS). 14 registered deterministic tools, durable background worker with atomic claims (`SKIP LOCKED`) and checkpoint recovery, Google Gemini adapter (`gemini-3.1-flash-lite`), OpenAI adapter, deterministic offline fallback, and live SSE streaming telemetry.
> - **Phase 5 (End-to-End Workflows & Replay)**: Complete (PASS). Canonical Loops A, B, and C; multi-format Decision Dossiers (JSON, CSV with injection escaping, XLSX via `openpyxl`, PDF via `pypdf`); exact-match offline golden replay traces for Loops A, B, and C.
> - **Phase 6 (Benchmark, Governance & Security)**: Complete (PASS). Benchmark task schema validation, strict score aggregation with bootstrap intervals, 27/27 security tests (CSRF, IP trust, IDOR scenario isolation, password security, Git repository secret scan).
> - **Phase 7 (Deployment & Operations)**: Complete (PASS). Deployment preflight CLI (`scripts/deployment_preflight.py` verifying 1 migration head and 5 checked keys), Next.js 14 production build (10/10 static pages compiled), and complete Playwright E2E journey suites (14/14 passed).

---

## 2. The Problem It Addresses

Small-scale entrepreneurs planning micro-enterprises (such as a neighbourhood retail grocery or a small food-processing/tiffin unit with small capital, e.g., an illustrative [ILLUSTRATIVE] ₹2–5 lakh):
- **Face fragmented public data**: Official census figures, district economic indicators, and banking statistics are dispersed across separate portals, frequently in disparate and legacy formats.
- **Struggle with complex government policies**: Central and state schemes (such as PMFME, PMEGP, or PM-MUDRA) span lengthy PDF guidelines with intricate eligibility matrices, making it difficult to determine real eligibility or actual cash-flow impact.
- **Lack access to commercial location intelligence**: Proprietary location intelligence tools cater predominantly to enterprise retail chains, leaving micro-enterprises without evidence-backed site comparison. *(Note: Competitor positioning and feature boundaries are preliminary research findings undergoing validation in Task P0-3).*
- **Suffer from AI "hallucinations"**: General-purpose AI assistants frequently fabricate scheme rules, interest rates, or local demand statistics, providing dangerously ungrounded advice.

ArthLens addresses this by uniting verified public datasets, deterministic financial and spatial models, and an autonomous AI planning agent governed by strict verification rules.

---

## 3. The Three Core User Workflows (Loops)

ArthLens structures user interactions into three distinct investigation loops:

```
+-----------------------------------------------------------------------------------+
| Loop A: Question to Verified Answer                                               |
| Input: Economic question or claim                                                 |
| Planned Process: Fetch indicators -> check units/geography -> verify provenance   |
| Output: Evidence-backed answer with source links, or a transparent data-gap report|
+-----------------------------------------------------------------------------------+
                                          |
+-----------------------------------------------------------------------------------+
| Loop B: Opportunity to Decision (Location & Feasibility)                          |
| Input: District, business type (retail/food), 2-3 candidate sites, capital        |
| Planned Process: Travel-time catchments (Dijkstra) -> Demand gravity (Huff) ->    |
|                  Monthly cash flow -> Monte Carlo risk -> Sensitivity analysis     |
| Output: Ranked comparison of candidate sites with explicit assumption labels      |
+-----------------------------------------------------------------------------------+
                                          |
+-----------------------------------------------------------------------------------+
| Loop C: Scheme to Financial Impact                                                |
| Input: Entrepreneur profile, business facts, and chosen scheme (or discovery)     |
| Planned Process: 3-valued logic rule evaluation -> Identify missing facts ->      |
|                  Compute exact loan schedule, moratorium interest, and subsidy    |
| Output: Precise eligibility verdict (Eligible / Ineligible / Unknown) and rupee   |
|         impact integrated into the business cash flow                             |
+-----------------------------------------------------------------------------------+
```

1. **Loop A (Question to Verified Answer)**: An entrepreneur asks a factual question (e.g., *"What is the bank credit-deposit ratio in my district?"*). The planned agent retrieves verified public data, checks compatibility, and produces an answer where every figure traces to an official source. If data is unavailable, it reports the gap instead of guessing.
2. **Loop B (Opportunity to Decision)**: An entrepreneur selects 2–3 candidate locations on a map for a business concept. The system computes travel-time catchment zones, estimates demand capture, models monthly revenues and costs, simulates risk scenarios (Monte Carlo), and provides a side-by-side comparison.
3. **Loop C (Scheme to Financial Impact)**: An entrepreneur checks which government support schemes apply to them. ArthLens evaluates official guidelines step-by-step using strict logic. If details are missing, it asks targeted questions. Once verified, it calculates the exact subsidy amount, interest schedule, and updates the cash-flow projection.

---

## 4. Proposed Technology Stack

| Layer | Technology | Architectural Role |
| :--- | :--- | :--- |
| **Frontend** | **Next.js (App Router), TypeScript, Tailwind CSS** | The web application interface seen by the user. Type-safe and responsive. |
| **Mapping & GIS** | **MapLibre GL JS & PMTiles** | Interactive maps reading vector map archives directly from object storage without requiring custom tile-server infrastructure. |
| **Data Visualization** | **Apache ECharts & Cytoscape.js** | ECharts renders financial fan charts and sensitivity tornado plots; Cytoscape.js renders the interactive Evidence Graph and Policy AST. |
| **Backend API** | **Python 3.14, FastAPI, Pydantic v2** | High-speed API layer with strict request/response data validation. |
| **Database & Spatial** | **PostgreSQL + PostGIS** | Relational database with geographic data extensions handling boundaries, spatial queries, and road networks. |
| **Asynchronous Jobs** | **Postgres Jobs Table (`FOR UPDATE SKIP LOCKED`)** | Reliable background job worker queue without adding external broker dependencies (no Redis or Celery in MVP). |
| **Numerics & GIS Math**| **NumPy, SciPy, GeoPandas, Shapely, Pint** | Deterministic calculations for spatial demand allocation, financial models, risk simulations, and unit safety. |
| **Agent Orchestrator** | **Custom Python State Machine** | Orchestrates agent planning, tool invocations, budgets, and state recovery. |
| **LLM Access** | **Unified `ILLMClient` Adapter** | Provider-agnostic interface with circuit breaker, prompt-injection firewall, and zero-cost offline replay mode. |
| **Testing** | **pytest, Hypothesis, Playwright** | Unit tests, property-based verification (Hypothesis), and end-to-end browser tests (Playwright). |

---

## 5. Architectural Concepts Explained in Simple Terms

- **Agentic**: Rather than following a rigid script, the AI agent can formulate a plan, select appropriate calculation tools, inspect intermediate findings, and adapt its next steps based on what data is available.
- **Epistemic Ledger**: A ledger (similar to an accounting ledger) that tracks knowledge. Every number stored knows whether it is an *observed fact*, an *official rule*, a *user assumption*, or a *modelled estimate*.
- **Evidence Gating**: A strict programmatic rulebook. Before any report is shown to a user, a verifier checks that claims do not exceed what the evidence supports (for example, stopping an LLM from presenting a district average as a specific village statistic).
- **Dijkstra's Algorithm**: An algorithm that finds the shortest travel routes on a road network to determine which areas can reach a business within 15, 30, or 60 minutes.
- **Huff Gravity Model**: A mathematical model that predicts how customers choose between competing stores based on store attractiveness and travel distance.
- **Monte Carlo Simulation**: Running thousands of simulated future scenarios with varying costs and demand levels to see the probability of running out of cash.
- **Kleene 3-Valued Logic**: Logic using three values: `True`, `False`, and `Unknown`. If an entrepreneur has not yet specified a required fact, the rule engine marks eligibility as `Unknown` and asks for that fact, rather than guessing.

---

## 6. Repository Layout Overview

```
arthlens/
├── frontend/               # Next.js web application (Atlas, Studio, Console)
├── backend/arthlens/       # Python FastAPI backend & core computational engines
│   ├── domain/             # Immutable data structures (Quantity, Scenario, BusinessProfile)
│   ├── ledger/             # Epistemic Ledger, DAG propagation, and verification specifications
│   ├── policy/             # AST rule engine with Kleene 3-valued logic
│   ├── geo/                # Road graphs, Dijkstra catchments, spatial disaggregation
│   ├── demand/             # Demand allocation strategies (Nearest, Huff)
│   ├── finance/            # Deterministic financial models, loan schedules, break-even
│   ├── simulation/         # Vectorized Monte Carlo and sensitivity analysis
│   ├── agent/              # Orchestrator, state machine, tool registry, recovery
│   └── llm/                # LLM client adapters, circuit breakers, replay engine
├── docs/                   # Authoritative specifications, architecture records, checklists
└── tests/                  # Unit, property, contract, integration, and e2e suites
```

---

## 7. Current Project Status

- **Phase 1 (Foundations & Persistence)**: **Complete**.
  - Immutable domain models, unit typing (Pint), Kleene 3-valued policy AST, Epistemic Ledger DAG, PostgreSQL + PostGIS schema (Alembic migrations 001–005), and JWT/RBAC security infrastructure.
- **Phase 2 (Data Pipelines & Spatial Hierarchy)**: **Complete**.
  - **P2-1 — Verified Dataset Ingestion and Persistence**: **Complete**.
    - Ingestion pipeline with four verified adapters: OSM road network & POIs (`DS-04`), LGD & Census 2011 demographics (`DS-05`), Central Government Scheme guidelines (`DS-08`), and Survey of India compliant administrative boundaries (`DS-09`).
    - Database persistence for registered sources, snapshot versions, normalized records, and epistemic quantities.
  - **P2-2 — National & District Geographic Hierarchy Expansion**: **Complete**.
    - Immutable `GeoUnit` domain model, canonical namespace formatting (`in`, `in:state:09`, `in:district:120`, `in:subdistrict:120:890`, `in:subdistrict:156:845`), and `GeoUnitRepository` implementations (InMemory & PostgreSQL/PostGIS).
    - Decoupled orthogonal coverage semantics: `coverage_status` (navigability: `NAVIGABLE`), `geometry_status`, `analytical_status` (`ANALYSABLE` vs `ANALYSIS_UNAVAILABLE`), and `census_code`.
    - Database check constraints via Alembic migration 007 (`check_geo_unit_coverage_status`, `check_geo_unit_geometry_status`, `check_geo_unit_analytical_status`).
    - Ingestion of official nationwide LGD master snapshots: 36 States/UTs (`lgd_states.csv`) and 763 Districts (`lgd_districts.csv`), establishing the 800-unit national baseline hierarchy.
    - Second-district acceptance verified: Varanasi (District LGD 187, Census 197) configured and navigated under Uttar Pradesh alongside Prayagraj without engine modification.
    - Boundary geometry and spatial status:
      - Only the Prayagraj pilot geometry is currently stored in PostGIS, where it is technically validated (`GEOMETRY_VERIFIED` for RFC 7946 / PostGIS polygon topology via `ST_IsValid`).
      - Technical validity denotes geospatial query soundness and does NOT certify an authoritative government boundary.
      - The remaining 762 baseline districts remain `GEOMETRY_MISSING`.
      - Modern nationwide boundary acquisition remains **`SOURCE-GATED`** pending licensing and acquisition of an approved modern nationwide boundary dataset.
      - Nationwide PMTiles vector tiles are **`NOT GENERATED`**; the PMTiles source gate is the lack of an approved modern nationwide boundary dataset, not merely a missing packaging pipeline.
    - Test database isolation enforced via exact database identity validation guard; persistent development database verified with zero mutation across test runs.
    - Backend regression results: **343 passed, 1 skipped (optional live data.gov.in retrieval test), 0 failed**.
  - **P2-3 — Data-Quality Layer and Staleness Flags**: **Complete**.
    - Authoritative quality vocabulary implemented: `CURRENT`, `INCOMPLETE`, `STALE`, `ESTIMATED`, `UNAVAILABLE`.
    - Strict deterministic precedence order for primary display state selection: `UNAVAILABLE > INCOMPLETE > STALE > ESTIMATED > CURRENT`, with preservation of all secondary issues and explanations.
    - Deterministic freshness evaluation with injected clock support and separate tracking of `as_of`, `publication_date`, `retrieval_date`, `ingestion_date`, and `evaluation_date`.
    - Verified Census 2011 10-year staleness policy (`max_age_days = 3650`): strictly `STALE` evaluated on 6 November 2026 while preserving `Kind.OBSERVED`; recent download timestamps never make historical observations current.
    - Missing data is strictly `UNAVAILABLE` (never silently numeric zero).
    - Epistemic ledger propagation and calculation gating: calculations inspecting stale evidence inherit `STALE_ANCESTRY` and are restricted to `SUITABLE_HISTORICAL_ONLY`; missing inputs fail closed via `GatedCalculationError`.
    - Atlas presentation contract implemented: stable design tokens, hex colors (`#22C55E`, `#EAB308`, `#F97316`, `#3B82F6`, `#94A3B8`), stroke styles, opacity, patterns, and self-contained interactive visual preview (`docs/atlas-quality-shading-preview.html`).
    - API endpoints: enriched `GET /geo/{id}/indicators` with quality shading and added `GET /geo/{id}/quality`.
    - Backend regression results: **374 passed, 1 skipped (optional live data.gov.in retrieval test), 0 failed**.
  - **P2-4 — Interactive Atlas UI & Epistemic Workspace**: **Complete**.
    - Boundary data architecture: `AdminBoundariesAdapter` (DS-09) and PostGIS geometry persistence integrated into `DatasetIngestionPipeline` (`step_9_persist`) and multistage `geo_loader.py`.
    - Dedicated dynamic boundary endpoint `GET /geo/{geo_id}/boundary` returning RFC 7946 GeoJSON FeatureCollection with DS-09 provenance and RBAC gating.
    - AtlasMap robust boundary rendering: Explicit resolution states (`LOADING`, `RESOLVED`, `ERROR`), request sequence counter to eliminate stale boundary rendering race conditions, and immediate clearing of previous boundary.
    - Elimination of universal/blocking modal warning boxes on geographic selection: non-obstructive compact status pills and complete decoupling of geographic selection from data availability.
    - Anti-fabrication guarantees: Prayagraj polygon is never displayed for unmapped units (Varanasi, Bhopal, Jaipur); no fake boundaries or fake coordinates.
    - ProvenanceDrawer and EvidenceGraph epistemic integrity: strictly Floors 1–4 per Handbook Section 4.2 (`UNAVAILABLE` is a QualityStatus token, not an evidence floor).
    - Mobile responsiveness: zero horizontal navigation clipping at 390×844 viewport.
    - Verification: 11/11 boundary integration tests, 24/24 Vitest frontend unit tests, and 10/10 Playwright E2E browser tests passing.
- **Phase 3 (Computational Engines & Scenario Modeling)**: Next phase in active development (P3-1 Dijkstra catchments, P3-2 Huff spatial allocation, P3-3 financial feasibility, P3-4 Monte Carlo, P3-5 policy AST rules, P3-6 scenario lab).
- **Phase 4 (Agent Orchestrator & Production Hardening)**: Planned subsequent phase; not started.
- **Authoritative Specification Document**: [ArthLens Build Handbook](docs/ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026).
