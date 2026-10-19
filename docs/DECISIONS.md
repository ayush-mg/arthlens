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
