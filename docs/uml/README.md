# ArthLens UML Architecture & Design Diagrams

This directory contains the authoritative PlantUML (`.puml`) source files representing the architectural, behavioral, and functional models of the ArthLens system, developed in accordance with **ArthLens Build Handbook v1.0**.

---

## 1. Diagram Index & Overview

| File | Diagram Type | Core Subject | Handbook Reference | Status |
| :--- | :--- | :--- | :--- | :--- |
| [`use_case.puml`](file:///c:/arthlens/docs/uml/use_case.puml) | UML Use Case Diagram | System boundary, primary MVP actors, deferred future actors, implemented vs planned workflows. | Part 2.1, Part 5.5 | Baseline Defined (P1-7) |
| [`class_diagram.puml`](file:///c:/arthlens/docs/uml/class_diagram.puml) | UML Class Diagram | Domain entities, Epistemic Ledger, ORM models, Repositories, Security & API structure, Planned concepts. | Part 3.3, Part 5.5, Part 9 | Baseline Defined (P1-7) |
| [`agent_run_state_machine.puml`](file:///c:/arthlens/docs/uml/agent_run_state_machine.puml) | UML State Machine Diagram | 13-state AgentRun lifecycle, 4 terminal states, retry limits, budget exhaustion vs quota separation, gated actions. | Part 8.1, Part 8.2 | Target Specified (P1-7; Execution Engine Phase 4) |

---

## 2. Implementation vs. Planned Mapping

To maintain fidelity and prevent architectural drift, the UML diagrams visually and syntactically distinguish between **currently implemented code** (P1-1 through P1-6) and **planned concepts** scheduled for future development phases.

### A. Use Case Scope Breakdown

| Actor | Tier | Status in Codebase | Workflows & Use Cases |
| :--- | :--- | :--- | :--- |
| **Entrepreneur** | MVP Primary | Authentication (`/auth/login`, `/auth/logout`) and run API stubs implemented (P1-6); registration, profile, orchestration, and report generation workflows planned (Phases 2–4). | **Implemented:** Authenticate Session, Logout/Token Revocation, Create & Branch Scenarios (`/scenarios`).<br>**Planned:** Register User Account (Phase 2), Define Business Profile (Phase 2), Autonomous AgentRun Orchestration (Phase 4), Interactive Clarification Dialog (Phase 4), Gated Action Sign-off (Phase 4), Generate Full Report (Phase 4), Stochastic Risk Simulation (Phase 3). |
| **Data Steward** | MVP Primary | Epistemic Ledger DAG (P1-3), Verifier V1–V9 & ReportRenderer (P1-4), PostGIS & Repositories (P1-5), Policy API (P1-6) implemented. | **Implemented:** Persist Quantities & Immutability, Trace Lineage & Provenance, Evaluate Verifier V1–V9, Format Verified Chips & Scan Free Numbers, Manage Draft Policy Rules (`/policy/rules`).<br>**Planned:** Automated Dataset Ingestion Pipeline (Phase 2), Policy AST & Evaluation Engine (Phase 3). |
| **Administrator** | MVP Primary | RBAC Matrix, Audit Logging, Token Revocation, Rate Limiting & Cost Caps fully implemented (P1-6). | **Implemented:** Inspect Users & Quotas (`GET /admin/users`), Enforce Rate Limits & Quotas, Inspect Security Audit Trail (`GET /admin/audit`). |
| **Customer / Community** | Release 1 | Deferred to Release 1 (greyed out in diagram). | Submit Local Demand Signals & Feedback. |
| **Investor / Funder** | Advanced | Deferred to Advanced (greyed out in diagram). | Access District Viability Benchmarks. |
| **Supplier / Buyer** | Advanced | Deferred to Advanced (greyed out in diagram). | Publish Procurement & Off-take Requests. |
| **Programme Officer** | Advanced | Deferred to Advanced (greyed out in diagram). | Monitor Scheme Disbursement & Impact Metrics. |

### B. Class Diagram Scope Breakdown

- **Implemented Classes (Solid border, exact match with Python codebase in `backend/arthlens/`):**
  - **Domain:** `Quantity` (exactly 18 dataclass fields, exact types, immutability), `SimulationMetadata` (exact integer seed handling, sample count, data versions), Enums (`Kind`, canonical `EvidenceLevel` with alias `EvidenceFloor`, canonical `ResolutionTier` with alias `ResolutionLevel`), interfaces (`DataProvider`, `DemandAllocator`, `SimulationModel`, `RuleNode`, `RuleVisitor`, `Tool`, `ILLMClient`, `RunState`, `Repository`), and domain repository interfaces (`QuantityRepository`, `UserRepository`, `PolicyRuleRepository`, `ScenarioRepository`).
  - **Ledger & Verification:** `Ledger` (pure Python topological DAG: `_quantities`, `_parents`, `_children`), `LedgerVerifier`, `VerificationSpecification` (ABC with `check(claim, ledger)`), `SpecResult`, `AndSpecification`, all 9 concrete specifications (`DerivationDowngradeSpec` V1 through `SimulationModelVersionSpec` V9), `VerificationReport`, `ReportRenderer` (`format_chip`, `render`), `AllowlistConfig`, `RenderResult`, `DownscalingRegistry`.
  - **Persistence & Infrastructure:** `PostgresQuantityRepository`, `PostgresUserRepository`, `PostgresPolicyRuleRepository`, `PostgresScenarioRepository`, along with in-memory implementations and SQLAlchemy models (`QuantityModel`, `SimulationRunModel`, `UserModel`, `RoleModel`, `UserRoleModel`, `AuditEventModel`, `RevokedTokenModel`, `RateLimitModel`, `GeoUnitModel`, etc.).
  - **Security & API:** `Role` (`ENTREPRENEUR`, `STEWARD`, `ADMIN`), `AuthenticatedUser`, `EndpointPolicy`, `EndpointPolicyRegistry`, `AuditService`, `RateLimiter` (`InMemoryRateLimiter`, `PostgresRateLimiter`), `TokenRevocationStore` (`InMemoryTokenRevocationStore`, `PostgresTokenRevocationStore`), and FastAPI middleware stack (`RateLimitingMiddleware`, `CSRFProtectionMiddleware`, `DenyByDefaultMiddleware`).
- **Planned Classes (Dashed border, grey background, tagged `<<planned — not implemented>>`):**
  - `AgentRun` & `ActionPlan` (Deferred to Phase 4 Orchestration).
  - Concrete `Tool` implementations (e.g., `CensusDataProviderTool`, deferred to Phase 2/4).
  - `BusinessProfile` (Deferred to Phase 2).
  - Concrete simulation models (`MonteCarloFinancialSimulation`, `GravityDemandAllocator`, deferred to Phase 3).
  - Policy AST nodes (`PolicyRuleAST`, deferred to Phase 3).

### C. AgentRun State Machine Breakdown

- **States (13 total):**
  - **Operational:** `CREATED`, `INTERPRETING`, `PLANNING`, `EXECUTING`, `OBSERVING`, `RECOVERING`, `AWAITING_USER`, `AWAITING_APPROVAL`, `VERIFYING`.
  - **Terminal (4 total, styled with red fill and double border):** `COMPLETED`, `FAILED`, `BUDGET_EXHAUSTED`, `CANCELLED`.
- **Transitions (Authoritative Handbook Part 8.2):**
  - `CREATED` $\rightarrow$ `INTERPRETING`
  - `INTERPRETING` $\rightarrow$ `PLANNING` / `AWAITING_USER`
  - `AWAITING_USER` $\rightarrow$ `PLANNING`
  - `PLANNING` $\rightarrow$ `EXECUTING` / `PLANNING` / `FAILED`
  - `EXECUTING` $\rightarrow$ `OBSERVING`
  - `OBSERVING` $\rightarrow$ `EXECUTING` / `RECOVERING` / `AWAITING_APPROVAL` / `VERIFYING`
  - `AWAITING_APPROVAL` $\rightarrow$ `approved`: `EXECUTING` | `rejected`: `CANCELLED`
  - `RECOVERING` $\rightarrow$ `EXECUTING` / `PLANNING` / `AWAITING_USER` / `FAILED`
  - `VERIFYING` $\rightarrow$ `COMPLETED` / `RECOVERING`
  - Any active state $\rightarrow$ `BUDGET_EXHAUSTED` (when active run hits its budget limit)
- **Run Budget vs. Daily Quota Separation:**
  - **Per-Run Cost Cap:** Evaluated at each execution step. Default initial value is $0.25 (configurable per run, not an immutable universal constant). Breaching this limit transitions the run to `BUDGET_EXHAUSTED`.
  - **Daily Run Quotas (e.g., 50 runs/day):** Enforced at the API boundary before run instantiation (`POST /runs` returns HTTP 429). It does **NOT** cause an AgentRun state machine transition.
  - **Daily Monetary Cap ($5.00/day):** Reserved at API boundary; reconciled mid-run.

---

## 3. How to Render the Diagrams

PlantUML files can be viewed and converted to PNG or SVG through multiple tools:

### Option 1: VS Code (Recommended)
1. Install the **PlantUML** extension by Jebbs (`jebbs.plantuml`).
2. Open any `.puml` file and press `Alt + D` (or right-click and select **Preview PlantUML**).
3. Right-click the preview to export as `.png` or `.svg`.

### Option 2: PlantUML CLI (Java)
Run the PlantUML standalone JAR from the project root:
```bash
# Render all diagrams to PNG
java -jar plantuml.jar -tpng docs/uml/*.puml

# Render all diagrams to SVG
java -jar plantuml.jar -tsvg docs/uml/*.puml
```

### Option 3: Online PlantUML Viewer
Copy the contents of any `.puml` file directly into [PlantText](https://www.planttext.com/) or the official [PlantUML Online Server](https://www.plantuml.com/plantuml/uml/).

---

## 4. Maintenance Rule

To preserve the utility and accuracy of ArthLens documentation:
1. **Zero Invented Concepts:** Every implemented class, method, attribute, and transition must match actual code in `backend/arthlens/`.
2. **Phase Synchronization:** When implementing components in Phase 2, Phase 3, or Phase 4, their respective stereotypes must be updated from `<<planned — not implemented>>` to implemented status.
3. **Exact Persistence Mapping:** Exact integer seed validation (`NUMERIC(20,0)`) and Quantity immutability rules must remain accurately reflected.
