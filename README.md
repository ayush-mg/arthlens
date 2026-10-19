# ArthLens

> **Status: Development in Progress — Phase 0: Project Setup, Documentation & Research Validation**
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

> *Note: ArthLens is currently in **Phase 0 (Project Setup and Research Validation)**. Application features, calculation engines, and user interfaces described below represent the intended architecture specified in the handbook and are not yet implemented.*

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
| **Backend API** | **Python 3.12, FastAPI, Pydantic v2** | High-speed API layer with strict request/response data validation. *(Note: Python 3.14.5 environment compatibility check pending in Phase 0).* |
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

- **Phase**: Step 0 / Phase 0: Project Setup, Documentation & Research Validation.
- **Active Focus**: Primary verification of public datasets, scheme PDF guidelines, pilot district readiness, and environment compatibility.
- **Authoritative Specification Document**: [ArthLens Build Handbook](docs/ArthLens_Build_Handbook.pdf) (v1.0, 17 Oct 2026).
