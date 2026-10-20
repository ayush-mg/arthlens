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
  - **Backend API**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, GeoAlchemy2. *(Note: Local Python 3.14.5 compatibility under investigation in Phase 0; target runtime remains Python 3.12).*
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
   - This technical decision record establishes that all empirical gate criteria are satisfied and documented.
   - Formal sign-off and adoption remain subject to final confirmation by the human developers (Developers A and B).
