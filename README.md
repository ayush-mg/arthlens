# ArthLens

> **Status: Development in Progress — Phase 2: In Progress (P2-1, P2-2 & P2-3 Complete)**
>
> *An agentic, evidence-gated economic decision engine for Indian micro-enterprises.*  
> **Authoritative Specification**: [ArthLens Build Handbook](docs/ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026)

---

## 1. What is ArthLens?

**ArthLens** is an open, evidence-governed decision-support platform designed to assist prospective micro-entrepreneurs in India in exploring two foundational questions:
1. **Is this small business idea economically viable?**
2. **Where within a district is the most promising location to set it up?**

Unlike conventional business dashboards that display static charts or generic AI chatbots that guess answers, ArthLens is architected around an **Epistemic Ledger**—a verifiable accounting system for data where **every single number is tagged with its origin, resolution, and certainty level**.

The core design principle of ArthLens is **evidence gating**: the system is designed to refuse to present estimates as observed facts, refuse to claim village-level precision when only district averages exist, and mandate that all financial calculations and policy eligibility checks are evaluated by deterministic, auditable code rather than large language model (LLM) guesswork.

> **Implementation Status & Scope Notice**:
> - **Phase 1 (Foundations & Core Domains)**: **Complete**.
> - **Phase 2 (Data Ingestion & Geographic Grounding)**: **In Progress**.
>   - **P2-1 — Verified Dataset Ingestion and Persistence**: **Complete**.
>   - **P2-2 — National & District Geographic Hierarchy Expansion**: **Complete**.
>   - **P2-3 — Data-Quality Layer & Staleness Flags**: **Complete**.
>   - **P2-4 — Interactive Atlas UI & Spatial Exploration**: **Next phase task; not started**.
> - **What is currently implemented**:
>   - **Evidence and domain infrastructure**: Immutable data types (`Quantity`, `EvidenceFloor`, `Kind`, Pint dimensional unit enforcement).
>   - **Verification and epistemic ledger**: Directed acyclic dependency graph tracking provenance, calculation lineages, and evidence floors.
>   - **Database persistence and authentication infrastructure**: PostgreSQL 16 + PostGIS integration, Alembic migrations (001–007), check constraints, role-based access control, and JWT authentication.
>   - **Four verified-source ingestion adapters**: Dedicated adapters with 10-step validation pipelines for OpenStreetMap (`DS-04`), LGD/Census 2011 (`DS-05`), Government Schemes (`DS-08`), and Administrative Boundaries (`DS-09`).
>   - **Normalized source-record and quantity persistence**: Structured persistence models for `sources`, `source_versions`, `source_records`, and `quantities`.
>   - **Nationwide geographic hierarchy and provider expansion**: Canonical geographic domain models (`GeoUnit`), repository contracts, official nationwide LGD master states (36) and districts (763) ingestion, and second-district configuration acceptance (Varanasi: LGD 187, Census 197).
>   - **Data-quality layer and staleness flags (P2-3)**: Five authoritative quality states (`CURRENT`, `INCOMPLETE`, `STALE`, `ESTIMATED`, `UNAVAILABLE`) with deterministic precedence (`UNAVAILABLE > INCOMPLETE > STALE > ESTIMATED > CURRENT`), MapLibre data-driven shading contracts, Census 2011 10-year rule enforcement, epistemic ledger calculation gating, and decoupled geographic navigation from quality states.
> - **Scope Boundary**: Higher-level analytical engines (Loop B Dijkstra/Huff spatial models, Monte Carlo risk simulation, agent orchestration) and frontend user interfaces (Next.js, MapLibre GL JS, Cytoscape.js) are subsequent phase deliverables and are not yet deployed.

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
- **Phase 2 (Data Pipelines & Spatial Hierarchy)**: **In Progress**.
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
      - Only the Prayagraj pilot geometry is currently stored in PostGIS, where it is technically validated (`GEOMETRY_VERIFIED` for RFC 7946 / PostGIS polygon topology).
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
  - **P2-4 (Atlas UI with MapLibre, Provenance Drawer & Evidence Graph)**: **Next task; not started**.
- **Phase 3 & Phase 4 (Computational Engines & Frontend UI)**: Planned future phases; not started.
- **Authoritative Specification Document**: [ArthLens Build Handbook](docs/ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026).
