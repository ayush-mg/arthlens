# Architecture and Engineering Decisions Record (ADR)

> **Document Status**: Authoritative Architecture Baseline
> **Source Specification**: [ArthLens Build Handbook](ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026)
> **Governing Rule**: Any architectural deviation from the handbook must be recorded here with explicit justification, alternatives considered, and an associated task ID. Do not make silent deviations.

---

## Template for Recording Future Deviations / Decisions

When a decision or deviation is proposed, use this format:

```markdown
### ADR-XXX: [Title of Decision or Deviation]
- **Status**: [PROPOSED | ACCEPTED | REJECTED | SUPERSEDED]
- **Date**: YYYY-MM-DD
- **Task ID**: [e.g., P1-3]
- **Handbook Reference**: [e.g., Section 4.2]
- **Deciders**: [Developer A, Developer B, Antigravity]

#### Context
What specific problem, unexpected constraint, or new requirement makes this decision or deviation necessary?

#### Decision
What exact change is being adopted?

#### Rationale & Alternatives Considered
Why was this choice selected over the alternatives? What simpler approaches were evaluated?

#### Consequences & Impact
- What parts of the codebase, interfaces, or tests are affected?
- Does this require updating UML diagrams (`docs/uml`) or contract tests?
```

---

## Settled Decisions (from Handbook v1.0)

### ADR-001: The Epistemic Ledger and Evidence-Gated Architecture
- **Status**: `ACCEPTED` (Handbook Part 0.2, Part 1.4, Part 4)
- **Decision**:
  1. The central technical contribution of ArthLens is the **Epistemic Ledger**. Every numeric value in the system is stored as an immutable `Quantity` record adhering strictly to the **13 conceptual fields** defined in Handbook Section 4.1:
     1. `id (UUID)`: Unique identifier.
     2. `definition_key`: Semantic definition (e.g., `population.total`, `scheme.pmfme.subsidy_rate`).
     3. `value + unit`: Magnitude and associated Pint unit (e.g., `INR`, `INR/month`, `kg/month`, `persons`, `dimensionless`).
     4. `kind`: Enumeration of base classes (`OBSERVED`, `POLICY_RULE`, `USER_ASSUMED`, `ESTIMATED`, `SCENARIO`, `CALCULATED`, `SIMULATED`).
     5. `evidence_floor`: Integer rank representing the weakest base class among all ancestors.
     6. `geo_unit_id + resolution`: The geographic unit represented and its hierarchical level (`NATION`, `STATE`, `DISTRICT`, `SUBDISTRICT`, `VILLAGE_URBAN`, `POINT`).
     7. `temporal support`: The `as_of` date, time period start/end, and rule validity dates (`effective_from` / `effective_to`).
     8. `uncertainty`: Structured uncertainty representation (`EXACT`, `INTERVAL(lo, hi)`, `DISTRIBUTION(name, params)`, `SAMPLES(ref)`, `UNQUANTIFIED`).
     9. `source_refs`: List of source references (version ID, URL, page, table, cell, retrieval date).
     10. `method_id + model_version`: Identifier of the algorithm/pipeline that produced the quantity and code git commit/model version.
     11. `parent_ids (UUID[])`: Transitive inputs forming a directed acyclic graph (DAG); cycles are strictly rejected.
     12. `quality_flags`: Explicit quality annotations (e.g., `STALE`, `INCOMPLETE_SOURCE`, `LOW_COVERAGE`, `CONTRADICTED`, `ROUNDED`).
     13. `license_meta`: Licence and attribution string of the source, passed to exports and UI displays.

  2. The LLM **never calculates math and never writes final numbers**. All numerical, geospatial, financial, and policy eligibility operations are executed by deterministic Python engines.
  3. **Rule G4 (Ledger-Only Rendering)**: The LLM generates text containing placeholders such as `{{q:UUID}}`. The `ReportRenderer` substitutes placeholders with formatted chips. Any raw numeric literal outside an explicit allowlist causes a verification failure and is rejected.
  4. Derived quantities strictly inherit the minimum evidence floor of their parent inputs:
     $$\text{OBSERVED} = \text{POLICY\_RULE } (4) > \text{USER\_ASSUMED } (3) > \text{ESTIMATED } (2) > \text{SCENARIO } (1)$$
  5. Derived quantities take the coarsest resolution among parents unless an approved, registered downscaling method (`popweight_v1`) is used.
  6. Outputs must pass nine modular verification specifications (V1 to V9) before reaching `COMPLETED`.

---

### ADR-002: Scope Tiers and MVP Boundaries
- **Status**: `ACCEPTED` (Handbook Part 2.1, 2.2, 2.3)
- **Decision**:
  1. **MVP Scope (Build First)**:
     - **Geography**: Exactly one pilot district (default candidate: Prayagraj, UP, subject to Phase 0 gate).
     - **Business Templates**: Exactly two business templates: (1) Neighbourhood Retail Grocery, (2) Small Food-Processing / Tiffin Unit.
     - **Schemes**: Exactly three schemes: PMFME, PMEGP, PM-MUDRA.
     - **User Roles with UI**: Entrepreneur, Data Steward, Administrator. (The database and RBAC layer support all 7 roles from day one, but only 3 get frontend screens in MVP).
     - **Workflows**: Loop A (Question to verified answer), Loop B (Opportunity to decision), Loop C (Scheme to financial impact).
     - **Screens**: Economic Atlas, Scenario Laboratory, Agent Console, Policy Workspace, Evidence Graph, Steward Workspace, Admin.
     - **Exports**: XLSX, PDF, JSON, CSV.
     - **Modes**: Live Agent Mode + Bit-Identical Replay Mode.
  2. **Deferred to First Release (R1)**: Second district via configuration, user data upload & Loop D, LLM-assisted rule extraction with steward sign-off, policy version AST diff, Sobol sensitivity analysis, Hindi translation with number-preservation checks, DOCX/PPTX export, and Customer/Investor roles.
  3. **Explicitly Rejected Features**: Generic economics chatbot, macro-economy simulation / LLM-as-simulator, district GDP forecasting, individual credit scoring, automatic submission of government applications, scraping private platforms, blockchain, and vector databases in MVP.

---

### ADR-003: Database and Persistence Architecture (Single Datastore Principle)
- **Status**: `ACCEPTED` (Handbook Part 3.2, Part 9)
- **Decision**:
  1. Use **PostgreSQL with PostGIS** as the single database for all persistence needs:
     - Relational tables for users, roles, audit logs, and policy documents.
     - PostGIS for spatial geometries (district/sub-district boundaries, road graphs, POI facilities).
     - JSONB for flexible AST rule trees, scenario parameters, and step mementos.
     - Arrays (`UUID[]`) with GIN indexing for the ledger ancestry DAG (`parent_ids`).
  2. **No Redis, No Celery, No Vector DB, No Graph DB in MVP**:
     - Background jobs are managed via a PostgreSQL `jobs` table using `SELECT ... FOR UPDATE SKIP LOCKED`.
     - Full-text search on policy documents uses standard PostgreSQL full-text search (`tsvector` / GIN).
     - Graph queries on the ledger DAG are handled directly in Python / SQL recursive CTEs.

---

### ADR-004: Technology Stack Selection
- **Status**: `ACCEPTED` (Handbook Part 3.2)
- **Decision**:
  - **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS.
  - **Map Rendering**: MapLibre GL JS reading static vector PMTiles archives directly from object storage (no custom tile server required).
  - **Graph & Tree Visualizations**: Cytoscape.js for both the Evidence DAG and Policy Rule AST.
  - **Charts**: Apache ECharts for tornado plots, cash-flow fan charts, and comparison histograms.
  - **Backend API**: Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, GeoAlchemy2. (Standardized on Python 3.14 across local, Docker, and CI environments).
  - **Numerics & Units**: NumPy, SciPy, pandas, GeoPandas, Shapely, Pint (for unit arithmetic safety). Dijkstra implemented using Python `heapq` and validated against NetworkX in tests.
  - **Auth**: Password hashing (argon2 or bcrypt) with JWT in `httpOnly` secure `SameSite` cookies; seeded demo accounts for evaluation.
  - **Live Streaming**: Server-Sent Events (SSE) reading from `run_events` table with polling fallback.

---

### ADR-005: Object-Oriented Design and Design Pattern Map
- **Status**: `ACCEPTED` (Handbook Part 5)
- **Decision**:
  - Code follows strict SOLID principles and targeted GoF design patterns where they solve concrete architectural needs:
    - **Strategy Pattern**: `DemandAllocator` (`NearestFacilityAllocator`, `HuffAllocator`), `SimulationModel`, and `OptimizationSolver`.
    - **State Pattern**: `RunState` subclasses (`InterpretingState`, `PlanningState`, `ExecutingState`, etc.) governing valid `AgentRun` transitions.
    - **Composite & Visitor Patterns**: `RuleNode` hierarchy (`AndNode`, `OrNode`, `NotNode`, `LeafPredicate`) with visitors (`EligibilityEvaluator` using Kleene 3-valued logic, `PolicyDiff`, `FinancialImpactExtractor`).
    - **Command & Template Method Patterns**: `Tool` base class enforcing `validate_input -> check_preconditions -> run_core -> verify_postconditions`.
    - **Decorator Pattern**: Cross-cutting tool wrappers for `BudgetEnforcement`, `TimeoutAndRetry`, `ProvenanceRegistration`, and `AuditLogging`.
    - **Adapter Pattern**: `DataProvider` implementations insulating external data sources with local test fixtures.
    - **Specification Pattern**: 9 modular verification specs combined via `AndSpecification`.
    - **Memento Pattern**: `ExecutionMemento` serialized after each step to allow worker kill and seamless resumption.

---

### ADR-006: Agent State Machine Lifecycle
- **Status**: `ACCEPTED` (Handbook Part 8.2)
- **Decision**:
  - The agent orchestrator runs as a formal finite state machine with 13 explicit states:
    - `CREATED`, `INTERPRETING`, `PLANNING`, `EXECUTING`, `OBSERVING`, `RECOVERING`, `AWAITING_USER`, `AWAITING_APPROVAL`, `VERIFYING`, `COMPLETED`, `FAILED`, `BUDGET_EXHAUSTED`, `CANCELLED`.
  - Illegal state transitions (e.g. attempting to transition from `COMPLETED` back to `PLANNING`) raise an explicit domain exception.
  - Terminal states are strictly: `COMPLETED`, `FAILED`, `BUDGET_EXHAUSTED`, `CANCELLED`.
  - Gated human approvals (such as publishing a scenario or approving a policy rule) pause execution into `AWAITING_APPROVAL`.

---

### ADR-007: LLM Layer Isolation and Prompt-Injection Defense
- **Status**: `ACCEPTED` (Handbook Part 8.6, Part 8.7)
- **Decision**:
  - No application module imports a provider SDK directly. All calls route through `ILLMClient.generate_structured()`.
  - The LLM receives untrusted inputs (PDF passages, user prompts) wrapped in strict security boundaries.
  - The agent planner can only propose tools from a registered, per-run allowlist. Free-form LLM text cannot authorize tool calls or modify execution budgets.
  - Test suites and evaluator demo runs utilize `ReplayLLMClient` (replay recorded golden traces) and `FakeLLMClient` (scripted responses) to ensure bit-identical, network-independent execution.

---

### ADR-008: Pilot District Selection (Prayagraj, UP) and Business Template Selection
- **Status**: `PROPOSED (Technically Supported; Pending Human Sign-Off by Developers A+B)`
- **Date**: 2026-10-21
- **Task ID**: `P0-4`
- **Handbook Reference**: Part 2.1, Part 7.3, Part 7.4, Part 13.1
- **Deciders**: Developer A, Developer B (Human approval required)

#### Context
Handbook Part 2.1 and Part 7.3 establish that the MVP build must focus strictly on exactly one pilot district and exactly two micro-enterprise business templates. Prayagraj (Uttar Pradesh) was designated as the default candidate district, subject to passing the formal Go/No-Go Gate defined in Handbook Section 7.3. Task P0-4 requires evaluating the candidate district against every gate criterion, confirming the two business templates, mapping their parameter sources and evidence classes, and identifying any feature that must be gated or disabled due to unresolved upstream data dependencies.

#### Decision
1. **Pilot District Selected**: **Prayagraj, Uttar Pradesh**
   - Standard LGD District Code: `175`
   - Historical Census 2011 Code: `175`
   - Parent State: Uttar Pradesh (`LGD State Code 09`)
   - Administrative Structure: 8 Sub-Districts / Tehsils (Sadar, Soraon, Phulpur, Handia, Karchhana, Bara, Meja, Koraon).
   - Core Urban Commercial Focus: Sadar Tehsil (Civil Lines, Katra, Chowk).

2. **Selected Business Templates**:
   - **Template 1**: **Neighbourhood Retail Grocery (Kirana / General Store)**
   - **Template 2**: **Small Food-Processing / Tiffin Unit (Micro-Food Enterprise)**

3. **Part 7.3 Go/No-Go Gate Evaluation Results for Prayagraj**:
   - **Criterion A: Usable Road Network & POIs**
     - *Evidence*: [`docs/data-sources/ds-04-osm.md`](data-sources/ds-04-osm.md).
     - *Verified Empirical Facts*: Live audit via OpenStreetMap API v0.6 on a 400m x 400m commercial bounding box in Civil Lines/Katra (lat 25.448–25.452, lon 81.834–81.838) confirmed **1,253 Nodes** and **202 Ways**, including secondary road vectors (`Subhash Chauraha`, `Sardar Patel Marg`) and commercial POIs (McDonald's, Trends, Central Bank of India, jewellery stores). Geofabrik daily mirror downloads verified accessible for UP regional extracts.
      - *Limitations & Geographic Scope Tiers (Handbook Section 7.4)*: The live API audit tested a 400m x 400m sample to inspect node-way topology and commercial tags without exceeding public API limits. The entire Prayagraj District (LGD `175`, 8 tehsils) satisfies the **Navigable Tier** in the Atlas (official boundaries, LGD codes, census demographics). For the **Analysable Tier** (Loop B site catchments and competitor POIs), high-density road graphs and commercial clusters are empirically verified in the urban core (Sadar Tehsil / Prayagraj City).
      - *Mitigation*: In peripheral rural tehsils where informal vendors are unmapped, the UI must render the mandatory **OSM Completeness Caveat** (Handbook Part 2.2, Capability 30): *"Competitor density is derived from OpenStreetMap and reflects mapped physical establishments. Informal, temporary, or unmapped rural vendors may not be captured."* Rural network dead-ends require extracting the Largest Strongly Connected Component (SCC). Bulk coverage is supported by regional Geofabrik extracts.
     - *Gate Status*: **`PASS (Approved with Completeness Caveat)`**
   - **Criterion B: Population at Demand Model Resolution with Explicit as_of Date**
     - *Evidence*: [`docs/data-sources/ds-05-lgd-crosswalk.md`](data-sources/ds-05-lgd-crosswalk.md) and [`docs/data-sources/ds-09-administrative-boundaries.md`](data-sources/ds-09-administrative-boundaries.md).
     - *Verified Empirical Facts*: Official Census 2011 Primary Census Abstract (PCA) crosswalked to LGD Master Directory gives total district population of **5,954,391** (Rank 1 in UP), 962,772 households, and broken down across all 8 constituent tehsils (Sadar: LGD 845, Soraon: LGD 843, Phulpur: LGD 844, Handia: LGD 846, Karchhana: LGD 847, Bara: LGD 848, Meja: LGD 849, Koraon: LGD 850).
     - *Explicit Temporal Support*: `as_of` date is **2011-03-01** (Census 2011 reference date).
     - *Limitations & Downscaling*: High temporal staleness requires the mandatory **`STALE`** quality flag on raw 2011 counts. Zone/catchment population is downscaled using the registered **`popweight_v1`** spatial downscaling method (Handbook Section 6.2), entering the ledger as **`ESTIMATED`** and passing conservation tests.
     - *Gate Status*: **`PASS (Approved with STALE flag and popweight_v1 requirement)`**
   - **Criterion C: At Least Three Current, Official, Fetched, and Readable Scheme Guidelines**
     - *Evidence*: [`docs/data-sources/ds-08-schemes.md`](data-sources/ds-08-schemes.md), [`docs/schemes/source_register.md`](schemes/source_register.md), [`docs/schemes/parameter_register.md`](schemes/parameter_register.md), and 9 primary PDF files stored in [`docs/schemes/source_files/`](schemes/source_files/).
     - *Verified Empirical Facts*: Three schemes verified directly from issuing ministry gazettes and guidelines with SHA-256 hashes and 42 `SOURCE_SUPPORTED` parameters:
       1. **PMFME (MoFPI)**: 35% credit-linked capital subsidy (max ₹10L), 10% own equity, 3-year SRF lock-in, negative list of 18 activities.
       2. **PMEGP (MoMSME/KVIC)**: 15%–35% margin money subsidy, ₹50L manufacturing cap, ₹20L service cap, mandatory Udyam registration, mandatory EDP training, 3-year TDR lock-in.
       3. **PM-MUDRA (DFS/MoF)**: ₹20L overall ceiling w.e.f. 24.10.2024 (Tarun Plus), Shishu/Kishor/Tarun brackets, 100% collateral-free, CGFMU guarantee, ₹0 capital subsidy.
     - *Gate Status*: **`PASS`**

4. **Business Template Parameter Mapping & Epistemic Taxonomies**:
   - **Template 1: Neighbourhood Retail Grocery**
     - *Sector*: Retail Trade / Non-Farm Commercial Service.
     - *Primary Schemes*: PM-MUDRA (Kishor/Tarun) and PMEGP (Service/Business category up to ₹20L). Ineligible under PMFME (excluded as pure retail trading).
     - *Capital Outlay (Capex)*: Shelving, refrigeration, storefront, POS terminal, initial inventory (₹2L–₹10L) — `USER_ASSUMED` / `ESTIMATED`.
     - *Operating Costs (Opex)*: Commercial rent, electricity, helper wages, utilities — `USER_ASSUMED` / `ESTIMATED`.
     - *Gross Margin*: 10%–20% on packaged FMCG, 15%–25% on staples — `USER_ASSUMED` / `ESTIMATED`.
     - *Spatial Demand*: 15-minute walking/driving catchment via Dijkstra (`DS-04`, `CALCULATED`); demographic demand via `popweight_v1` (`DS-05`, `ESTIMATED`); competitor kirana counts via OSM tags `shop=convenience/supermarket/general` (`DS-04`, `OBSERVED`).
     - *Upstream Dependency on DS-01 (Mandi Prices)*: **Zero dependency**. Retail grocery does not use daily agricultural mandi price feeds.
   - **Template 2: Small Food-Processing / Tiffin Unit**
     - *Sector*: Food Processing / Micro-Manufacturing.
     - *Primary Schemes*: PMFME (35% credit-linked capital subsidy up to ₹10L, 10% own equity margin; aligns with Prayagraj ODOP Guava processing or general food processing); PMEGP (Manufacturing up to ₹50L); PM-MUDRA (working capital).
     - *Capital Outlay (Capex)*: Kitchen/processing machinery, burners, packaging unit, utensils, delivery crates (₹2.5L–₹15L) — `USER_ASSUMED` / `ESTIMATED`.
     - *Operating Costs (Opex)*: Kitchen rent, commercial LPG, delivery wages, packaging consumables, FSSAI compliance — `USER_ASSUMED` / `ESTIMATED`.
     - *Spatial Demand*: Commercial/institutional POIs (offices, colleges, banks, markets) in OSM driving daily meal demand (`DS-04`, `OBSERVED`); 15–30 min delivery catchment via Dijkstra (`DS-04`, `CALCULATED`).
     - *Financing Invariants*: 3-year Subsidy Reserve Fund lock-in (`POLICY_RULE`, `PMFME-P05`); mandatory Udyam registration (`POLICY_RULE`, `PMEGP-P15`).
     - *CRITICAL FEATURE GATE: Upstream Dependency on DS-01*:
       - **Problem**: DS-01 (`data.gov.in` AGMARKNET mandi price endpoint) currently has an unresolved price unit issue (`PENDING` status; API returns numeric values without an explicit `unit` field).
       - **Binding Architectural Invariant**: To uphold the Epistemic Ledger's zero-unverified-numbers rule (Handbook Part 0.2), **automated raw material cost calculation from live DS-01 mandi prices is STRICTLY DISABLED in the MVP for Template 2.**
       - **Fallback Mode**: Raw material procurement costs (e.g. cost per meal / kg of flour/produce) must be directly provided as a `USER_ASSUMED` input by the entrepreneur or selected from a curated, steward-approved static benchmark fixture tagged as `ESTIMATED`. Dynamic mandi ingestion remains disabled until formal unit verification in Phase 2.

5. **Human Governance & Sign-Off Notice**:
   - P0-4 is categorized as **Human-Owned (`A + B`)** in the Build Handbook (Part 13.1).
   - Formal sign-off and adoption confirmed by human developer on 2026-10-21: Prayagraj confirmed as MVP pilot district under the Two-Tier Geographic Coverage Policy and DS-01 safety restriction.

---

### ADR-009: Hosting Limits, Deployment Architecture, and LLM Provider Selection (Task P0-6)
- **Status**: `ACCEPTED` (Handbook Parts 3.1, 3.2, 8.3, 8.6, 14.1–14.5; Detailed audit in [`docs/hosting-and-llm-decision.md`](hosting-and-llm-decision.md))
- **Decision Date**: 2026-10-21
- **Context**: Task P0-6 requires confirming hosting constraints and LLM provider terms against current official primary documentation, resolving or recording all open questions, and locking down the deployment topology before Phase 1 code is written.

- **Key Architectural Decisions**:
  1. **Tiered Hosting Topology**:
     - **Local Development**: Docker Compose running PostgreSQL 16 + PostGIS 3.4 (`postgis/postgis:16-3.4-alpine`), local FastAPI backend, Next.js dev server, and `FakeLLMClient` with zero external dependencies and zero API costs.
     - **Public Academic Demonstration**:
       - *Frontend*: **Cloudflare Pages** (Free tier: unlimited bandwidth, commercial use allowed) with **Vercel Hobby** as an educational fallback.
       - *Backend API & Worker*: **Render Starter ($7/mo always-on)** or **Hugging Face Spaces (`cpu-basic`, 16 GB RAM Docker free tier)**. Free Render Web Service sleeps after 15 min and lacks free workers; hence, long-running agent jobs must not rely on sleeping free containers without in-process async worker loops or Replay Mode.
       - *Database*: **Neon Postgres (Free tier, 1 GB storage, 100 CU-hours/mo)** or **Supabase (Free tier, 500 MB)** with native PostGIS. Render Postgres Free is explicitly rejected for deployment due to its mandatory 30-day deletion rule.
       - *Object Storage*: **Cloudflare R2 (Free tier, 10 GB standard, $0.00 egress)**. S3 is designated secondary due to $0.09/GB egress risk on public vector tile downloads.
       - *Demo Reliability Safeguard*: **Replay Mode** (Handbook Part 14.4) serves pre-recorded golden traces for Loops A, B, and C with the `REPLAY` banner, guaranteeing rock-solid demos even if cloud providers sleep or hit rate limits.
  2. **LLM Provider & Access Layer**:
     - **Primary Production Provider**: **OpenAI API**
       - Primary workhorse: **`gpt-6-luna`** ($0.10/1M input, $0.50/1M output, $0.01 cached, ~1.05M context, guaranteed JSON Schema enforcement with `strict: true`). Replaces `gpt-4o-mini` (officially deprecated Oct 14, 2026; API shutdown Jan 14, 2027).
       - Complex reasoning & PDF extraction fallback: **`gpt-5.6-terra`** ($2.00/1M input, $12.00/1M output).
     - **Alternative Compatible Providers**: **Anthropic** (`claude-3-5-haiku` / `claude-3-5-sonnet`) and **Google Gemini** (Paid tier only). Note: Google AI Studio Free tier is rejected for sensitive enterprise data because user prompts are harvested for model training.
     - **Contractual Privacy Guarantee**: OpenAI API and Anthropic API terms guarantee that API inputs/outputs are **NOT used to train models**.
     - **Provider Decoupling**: All LLM calls pass through the `ILLMClient` abstraction. No domain or agent module may directly import provider SDKs.
  3. **Cost Governance Invariants**:
     - Initial per-run cost cap: `MAX_COST_USD_PER_RUN = 0.25` enforced in code by `BudgetEnforcementDecorator` (provides ~62x safety margin with `gpt-6-luna`).
     - Hard step limit: 25 steps; Replans: 3; Model calls: 30; Tool timeout: 60s; Retries: 2.
     - Offline testing: `FakeLLMClient` and `ReplayLLMClient` ensure 100% test coverage and CI execution without incurring API costs.

---

### ADR-010: Epistemic Ledger Implementation, Pint Unit Registry, and Downscaling Registry (Task P1-3)
- **Status**: `ACCEPTED` (Handbook Parts 4.1–4.4, 4.7, 5.1)
- **Date**: 2026-10-22
- **Task ID**: `P1-3`
- **Handbook Reference**: Section 4.1, 4.2, 4.3, 4.4, 4.7, 5.1
- **Deciders**: Developer A, Antigravity

#### Context
Task P1-3 establishes the foundational computational substrate of ArthLens: the immutable `Quantity` domain model, the Epistemic Ledger DAG, evidence floor combination, resolution downscaling with conservation, uncertainty propagation, and Pint unit-compatibility checking to make all 27 original P0-5 invariant tests pass.

#### Decision
1. **Quantity Dataclass**:
   - Implemented as `@dataclass(frozen=True)` in `backend.arthlens.domain.quantity` adhering to the 16 model attributes specified in Handbook Section 5.1 and ADR-001.
   - Immutability is enforced at runtime (`FrozenInstanceError` on modification).
   - Invariants validated in `__post_init__`: `kind` in `Kind`, `evidence_floor` in $[1, 4]$, `resolution` in $[0, 5]$, and strict rejection of `OBSERVED` quantities declaring parent inputs.
2. **Epistemic Ledger DAG (`backend.arthlens.ledger.ledger.Ledger`)**:
   - In-memory DAG maintaining registered quantities, parent edges, and child edges.
   - Prohibits direct self-reference (`quantity.id in quantity.parent_ids`) and indirect multi-node directed cycles during registration by verifying that `quantity.id` is not an ancestor of any declared parent.
   - `ancestors(id)` returns the exact set of transitive parent IDs, verified on linear chains and diamond dependencies.
3. **Pint Unit Registry (`backend.arthlens.ledger.units`)**:
   - Custom `UnitRegistry` adds domain currencies (`INR`, `rupee`, `rupees`), headcount (`person`, `persons`), and Indian multiples (`lakh`, `crore`).
   - `check_unit_compatibility` validates dimensional consistency for operations (`add`, `subtract`, `multiply`, `divide`), raising `DimensionalityError` (a `ValueError` subclass) when adding incompatible dimensions (e.g. `INR` + `kg`, `INR` + `INR/month`).
4. **Downscaling Registry & `popweight_v1` (`backend.arthlens.ledger.downscaling`)**:
   - `DownscalingRegistry` manages registered spatial downscaling algorithms. Unregistered methods are strictly rejected.
   - `popweight_v1` partitions coarse district totals to zones according to weights and strictly conserves totals within floating-point tolerance ($\sum E_z = D_{\text{district}}$).
5. **Uncertainty Arithmetic & Combination (`backend.arthlens.ledger.uncertainty`)**:
   - `UNQUANTIFIED` is contagious for all deterministic operations.
   - `EXACT` inputs combined deterministically remain `EXACT`.
   - Interval arithmetic correctly encloses exact arithmetic for addition, subtraction, and multiplication.
   - Division by an interval containing zero is strictly rejected with `ZeroDivisionError`.
6. **Quality Flag Propagation (`backend.arthlens.ledger.propagation`)**:
   - Derived quantities inherit all parent quality flags (`STALE`, `INCOMPLETE_SOURCE`, `LOW_COVERAGE`, etc.) as a unified `frozenset`.


---

### ADR-011: P1-5 Persistence Architecture: PostgreSQL Schema, Seed Precision, and Dual Repositories
- **Status**: `ACCEPTED` (Handbook Part 5.1, Part 9.1, Part 9.2, Part 12.1, Part 13.1, Appendix A.2)
- **Date**: 2026-10-30
- **Task ID**: `P1-5`
- **Handbook Reference**: Part 5.1, Part 9.1, Part 9.2, Part 12.1, Part 13.1, Appendix A.2
- **Deciders**: Developer A, Antigravity

#### Context
Task P1-5 translates the Handbook Part 9 candidate schema into version-controlled Alembic migrations against PostgreSQL 16 + PostGIS 3.4, implements repository interfaces following the P1-2 `Repository` contract, provides both PostgreSQL-backed and in-memory fake implementations with identical semantics, guarantees Quantity immutability at the database boundary, and ensures full round-trip preservation of Quantity records including P1-4 `SimulationMetadata` with exact unsigned 64-bit seed precision.

#### Decision
1. **PostgreSQL/PostGIS Schema & Alembic Migration Structure (`backend/migrations/`)**:
   - Baseline migration `001_initial_schema.py` establishes all 20 tables defined in Handbook 9.1 and 9.2:
     - Identity & RBAC: `users`, `roles`, `user_roles`
     - Evidence & Provenance: `sources`, `source_versions`
     - Geography & Facilities: `geo_units` (PostGIS `geometry`), `facilities` (PostGIS `geometry`)
     - Core Epistemic Ledger: `quantities` (UUID PK, `parent_ids UUID[]` indexed via `quantities_parents_gin USING GIN`, `uncertainty JSONB`, `source_refs JSONB`, `simulation_meta JSONB`)
     - Policy & Governance: `policy_documents`, `policy_rules`
     - Profiles & Scenarios: `business_profiles`, `scenarios`, `simulation_runs`
     - Agent Orchestration: `agent_runs`, `agent_run_steps`, `run_events`
     - Jobs & Auditing: `jobs`, `approvals`, `tasks`, `audit_events`
   - Migration `002_seed_and_immutability.py`:
     - Installs PostgreSQL trigger `trg_quantities_immutable` via function `enforce_quantity_immutability()` to enforce database-boundary immutability of Quantity `value` and `kind`.
     - Expands `simulation_runs.seed` from `BIGINT` to `NUMERIC(20, 0)` with a downgrade safety check refusing downgrade if records with `seed > 9223372036854775807` exist.
   - Migration `003_enforce_exact_integer_seed.py`:
     - Refines `simulation_runs.seed` to unconstrained `NUMERIC` with check constraint `CHECK (seed = TRUNC(seed) AND seed >= 0 AND seed <= 18446744073709551615)`. This prevents PostgreSQL from silently auto-rounding fractional inputs prior to check constraint evaluation, strictly rejecting fractional seeds. Includes downgrade safety check guarding against fractional seeds.
   - Verified clean migration cycles: `alembic upgrade head`, `alembic downgrade base`, and intermediate version rollbacks/re-upgrades execute cleanly against PostgreSQL 16 + PostGIS 3.4.

2. **Quantity Immutability & Supersession Invariant**:
   - Handbook Section 9.2: *"Quantities are immutable: never UPDATE value or kind. Corrections create a new quantity and mark the old one superseded in quality_flags."*
   - Application Layer: `PostgresQuantityRepository` and `InMemoryQuantityRepository` reject mutation attempts on existing IDs with `ImmutableQuantityError`.
   - Database Engine Layer: PostgreSQL trigger `trg_quantities_immutable` intercepts direct SQL `UPDATE` statements on `quantities` and aborts if `NEW.value IS DISTINCT FROM OLD.value` or `NEW.kind IS DISTINCT FROM OLD.kind`.
   - Supersession Updates: Updates modifying non-immutable metadata (such as appending `'SUPERSEDED'` to `quality_flags`) are explicitly permitted at both layers.

3. **Exact Unsigned 64-Bit Simulation Seed Persistence**:
   - P1-4 `SimulationMetadata` supports PCG64 random seeds up to $2^{64}-1$ ($0 \le \text{seed} \le 18446744073709551615$). Standard signed PostgreSQL `BIGINT` caps at $9223372036854775807$ and overflows for unsigned 64-bit values.
   - Input Validation (`backend/arthlens/domain/simulation.py`): `validate_and_convert_seed(raw_seed)` strictly rejects `bool` (subclass of int), `float` (to prevent IEEE-754 precision loss), fractional `Decimal`, negative integers, and values $> 18446744073709551615$. Valid integers and integral Decimals are converted to `Decimal(val)` for persistence.
   - SQLAlchemy Precision Mapping: Mapped as `Numeric(asdecimal=True)` on `SimulationRunModel.seed`. Setting `asdecimal=True` guarantees that SQLAlchemy returns Python `Decimal` rather than binary64 floats.
   - Lossless Retrieval: Repositories convert from `Decimal` to Python `int` via `int(model.seed)`, achieving bitwise integer equality with zero floating-point intermediate representations. Tested against precision boundaries $0$, $1$, $9007199254740993$ ($2^{53}+1$), and $18446744073709551615$ ($2^{64}-1$).

4. **SimulationMetadata Storage in Quantities**:
   - `SimulationMetadata` represents reproducible Monte Carlo parameters (scenario ID, model version, unsigned 64-bit seed, sample count $N$, and input data versions).
   - In `QuantityModel`, stored in a dedicated `simulation_meta JSONB NULL` column on `quantities`, preserving domain encapsulation without overloading `source_refs` or encoding structured parameters into `method_id`.

5. **Dual Repository Architecture**:
   - Abstract interfaces in `backend.arthlens.domain.repositories`: `QuantityRepository`, `UserRepository`, `PolicyRuleRepository`, `ScenarioRepository`.
   - `InMemoryQuantityRepository` (and sibling in-memory repositories) provide isolated unit/contract test execution with zero external database dependencies.
   - `PostgresQuantityRepository` (and sibling PostgreSQL repositories) provide persistent production storage, utilizing SQLAlchemy 2.0 with GIN index array containment (`parent_ids.contains([target_uuid])`) for DAG child navigation.
   - Contract test suite `backend/tests/contract/test_repository_contracts.py` parametrizes both implementations across 24 test cases, enforcing identical domain contracts.

6. **Continuous Integration & Testing**:
   - `.github/workflows/ci.yml` updated to install `sqlalchemy`, `alembic`, `geoalchemy2`, and `psycopg[binary]`.
   - CI environment runs migrations against the `postgis/postgis:16-3.4-alpine` service container and executes contract and integration tests alongside existing unit and property suites.
   - 192 total backend tests pass under Python 3.14.5.

---

### ADR-012: P1-6 Authentication, Roles, RBAC, Audit Immutability, and Concurrency-Safe Rate Limiting
- **Status**: `ACCEPTED` (Handbook Part 9, Part 10.1, Part 11, Part 12, Part 13.1 P1-6, Appendix A.0, A.2)
- **Date**: 2026-10-31
- **Task ID**: `P1-6`
- **Handbook Reference**: Part 9 (audit_events), Part 10.1 (permission matrix), Part 11 (security & rate limiting), Part 12 (testing), Part 13.1 (P1-6 acceptance), Appendix A.0, Appendix A.2
- **Deciders**: Developer A, Antigravity

#### Context
Milestone P1-6 implements authentication, role-based authorization, append-only audit event persistence, IDOR prevention, and distributed concurrency-safe rate limiting and quota enforcement. The implementation must adhere strictly to the Handbook Part 10.1 Permission Matrix, enforce deny-by-default behavior, prevent account enumeration, safeguard sensitive credentials from audit logs, ensure database-engine-level immutability on audit logs, and provide multi-process atomic rate limiting without introducing external runtime dependencies such as Redis or Celery.

#### Decision

1. **Password Security & Verification (Argon2id RFC 9106)**:
   - Passwords are hashed using Argon2id (`Type.ID`) via `argon2-cffi` configured with production-grade parameters:
     - Memory cost: $65,536\text{ KiB}$ ($64\text{ MiB}$)
     - Time cost: $3\text{ iterations}$
     - Parallelism: $4\text{ lanes}$
     - Salt length: $16\text{ bytes}$
     - Hash length: $32\text{ bytes}$
   - Constant-time verification is performed using `argon2.PasswordHasher.verify`.
   - Generic failure responses: `POST /auth/login` returns an identical `401 Unauthorized` with `{"detail": "Invalid email or password."}` whether the email does not exist or the password is incorrect. To prevent timing side-channel attacks for account enumeration, a dummy hash verification is executed when an unknown email is encountered.
   - Password strength validation requires a minimum of 12 characters, including at least one uppercase letter, one lowercase letter, one decimal digit, and one symbol/punctuation mark.

2. **JWT Session Architecture, Authoritative Role Freshness & Revocation**:
   - Authentication tokens are signed using HMAC-SHA256 (`HS256`, configurable to RS256/EdDSA via `JWT_ALGORITHM`), carrying RFC 7519 standard claims:
     - `sub`: User UUID string
     - `email`: User email address
     - `roles`: List of assigned role strings (e.g. `["ENTREPRENEUR"]`)
     - `jti`: Unique token UUID identifier
     - `iat`: Epoch timestamp of issuance
     - `exp`: Expiration epoch timestamp (default 30 minutes, configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
   - Transport & Dual Authentication Model:
     - Web browser sessions use HTTP-only, SameSite (`lax`), Secure (HTTPS in production via `AUTH_COOKIE_SECURE`) cookies (`arthlens_access_token`).
     - Machine/API/CLI clients are supported via standard `Authorization: Bearer <token>` headers.
     - CSRF defense-in-depth: `CSRFProtectionMiddleware` strictly inspects `Origin` and `Sec-Fetch-Site` headers for cookie-authenticated state-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`). Bearer-token requests are immune to CSRF and exempt.
   - Authoritative Role Freshness:
     - To ensure that role revocations or promotions take effect immediately without waiting for token expiry, `get_current_user` re-validates the subject against the authoritative database (`PostgresUserRepository.get_by_id`). Demoted or deactivated accounts are rejected on the very next request.
   - Token Revocation: On `POST /auth/logout`, the token's `jti` is permanently committed to the PostgreSQL `revoked_tokens` table. `decode_access_token` checks cryptographic validity and the revocation store. A bulk pruning routine `prune_expired_tokens` clears records past their natural JWT expiry.

3. **Three MVP Roles & Centralized RBAC Matrix (Handbook Part 10.1)**:
   - Defined three canonical roles in `Role` enum: `ENTREPRENEUR`, `STEWARD`, `ADMIN`.
   - Deny-by-default enforcement: `EndpointPolicyRegistry` centrally registers every permitted method/path combination with its authorized roles and owner-only requirement. `DenyByDefaultMiddleware` intercepts all requests; any route or HTTP method not explicitly registered is rejected with `404 Not Found` or `403 Forbidden`.
   - Declarative FastAPI dependencies:
     - `get_current_user`: Extracts, validates, and decodes session cookie or Bearer token into an `AuthenticatedUser` model.
     - `require_roles(*roles)`: Verifies role membership and raises `403 Forbidden` (`detail: "Insufficient permissions for this resource."`) if unprivileged.
   - Enforced route permission matrix:
     - `POST /runs`: `ENTREPRENEUR`
     - `GET /runs/{id}`, `GET /runs/{id}/events`: Owner or `ADMIN`
     - `POST /runs/{id}/answer`: Owner only
     - `POST /runs/{id}/approve`: Owner or `STEWARD`
     - `POST /scenarios`, `POST /scenarios/{id}/branch`: `ENTREPRENEUR` (Owner only on branch)
     - `GET /policy/rules`: All authenticated roles
     - `POST /policy/rules`: `STEWARD` only
     - `GET /geo/{id}/indicators`, `GET /ledger/{id}`, `GET /replay/{id}`: All authenticated roles (and demo access)
     - `GET /admin/users`, `GET /admin/audit`: `ADMIN` only

4. **Resource Scoping & IDOR Prevention**:
   - Access control for user-specific resources (`scenarios`, `simulation_runs`, `agent_runs`) and private epistemic ledger records (`quantities`) is scoped at both the service layer and the repository layer (`get_scenario_by_id_and_owner`, `get_run_by_id_and_owner`).
   - Per-record quantity access on `GET /ledger/{quantity_id}`:
     - Public quantities (`owner_id IS NULL`) are accessible to all authenticated roles.
     - User-owned private quantities (`owner_id IS NOT NULL`) are strictly restricted to the owning user and `ADMIN`.
   - Existence Masking: When User B attempts to access or mutate an object owned by User A, the endpoint responds with `404 Not Found` (`{"detail": "Resource not found."}` or `{"detail": "Quantity not found."}`) identical to non-existent records, preventing resource enumeration.

5. **Append-Only Audit Trail & Database Engine Immutability**:
   - `audit_events` table stores immutable records: `id` (UUID), `actor_id` (UUID), `action` (VARCHAR), `resource_type` (VARCHAR), `resource_id` (UUID), `payload` (JSONB), `event_hash` (VARCHAR(64)), `created_at` (TIMESTAMPTZ).
   - PostgreSQL engine boundary: Migration `004_auth_immutability_and_roles.py` installs trigger `trg_audit_events_immutable` via function `enforce_audit_events_immutability()` rejecting any direct SQL `UPDATE` or `DELETE` on `audit_events`.
   - Redaction & Hashing: `AuditService` automatically sanitizes payload dictionaries before persistence, redacting sensitive keys (`password`, `password_hash`, `token`, `secret`, `cookie`, `credential`) to `'[REDACTED]'`, and computes deterministic SHA-256 event hashes.

6. **Distributed Concurrency-Safe Rate Limiting, Cost Caps & Quotas (No Redis)**:
   - In accordance with the single-datastore architecture (Handbook Part 3.1 & 3.2), rate limiting is implemented directly in PostgreSQL via table `rate_limits (key VARCHAR PRIMARY KEY, count INT, reset_at TIMESTAMPTZ)`.
   - `PostgresRateLimiter` executes an atomic PostgreSQL statement:
     ```sql
     INSERT INTO rate_limits (key, count, reset_at)
     VALUES (:key, 1, NOW() + (:window_seconds || ' seconds')::interval)
     ON CONFLICT (key) DO UPDATE
     SET count = CASE WHEN rate_limits.reset_at <= NOW() THEN 1 ELSE rate_limits.count + 1 END,
         reset_at = CASE WHEN rate_limits.reset_at <= NOW() THEN NOW() + (:window_seconds || ' seconds')::interval ELSE rate_limits.reset_at END
     RETURNING count, GREATEST(0, EXTRACT(EPOCH FROM (reset_at - NOW()))::int) AS reset_in;
     ```
     Guarantees zero race conditions across multi-process workers without Redis. Storage growth is bounded via `prune_expired_entries()`.
   - Trusted Proxy IP Resolution: `RateLimitingMiddleware` verifies direct client IPs against `get_trusted_proxies()` before honoring `X-Forwarded-For`, preventing IP spoofing.
   - Throttling & Quota Thresholds:
     - Per-IP limit: 60 requests/minute (provisional default, unverified in Handbook).
     - Per-User limit: 120 requests/minute (provisional default, unverified in Handbook).
     - Daily run quota: 50 runs/day per entrepreneur (provisional default).
     - Daily accumulated cost cap: $5.00/day per entrepreneur (provisional ceiling).
     - Single-run cost cap: $0.25/run (Handbook Part 8.3 baseline, verified starting point).
   - Pre-Execution Cost-Cap & Atomic Concurrency:
     - `POST /runs` validates `max_cost_usd` and `estimated_cost_usd` against `MAX_COST_USD_PER_RUN` ($0.25) before initiating any simulation.
     - `PostgresUserRepository.increment_quota_counters` utilizes PostgreSQL `SELECT ... FOR UPDATE` row-level locking on `users` to serialize concurrent requests and eliminate lost updates.

7. **Database Migration & Seeding**:
   - Migration `004_auth_immutability_and_roles.py`:
     - Creates `revoked_tokens` table with index on `expires_at`.
     - Creates `rate_limits` table with index on `reset_at`.
     - Seeds baseline MVP roles: `ENTREPRENEUR`, `STEWARD`, `ADMIN`.
     - Installs `trg_audit_events_immutable` trigger.
     - Full rollback / downgrade support verified.

8. **Verification & Test Coverage**:
   - 248 total backend tests pass cleanly under Python 3.14.5 with zero failures across smoke, property, unit, contract, and integration suites.
   - 56 total security, auth, RBAC, audit, cost-cap, and rate-limiting tests added across unit, contract, and integration layers.
