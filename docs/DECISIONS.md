# Architecture and Engineering Decisions Record (ADR)

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform
**Baseline Commit:** `fe11829`
**Governing Equation:** $$\text{ArthLens} = \text{Business Operating System} + \text{Financial Intelligence} + \text{Decision Intelligence} + \text{Agentic AI}$$

---

## ADR Index

1. **ADR-001**: Retirement of Geography-First Atlas in Favor of Business Operating System
2. **ADR-002**: Pure Deterministic Arithmetic for Financial & Decision Calculations
3. **ADR-003**: Domain-Driven Design & Strict Aggregate Boundaries
4. **ADR-004**: Multi-Tenant Isolation with Request-Authorized Execution Context
5. **ADR-005**: Typed Decision Evaluation Graph with Multi-Alternative Ranking
6. **ADR-006**: Agentic AI Co-pilot with Strictly Bound Tenant Execution Context
7. **ADR-007**: PostgreSQL 16 Storage with Preserved Migration Lineage
8. **ADR-008**: Next.js 14 Liquid-Glass Architecture with Constellation Overview

---

### ADR-001: Retirement of Geography-First Atlas in Favor of Business Operating System
- **Status**: `ACCEPTED`
- **Context**: The previous product attempted to solve micro-entrepreneurship through geographic indicators, spatial road graphs, and district-level economic atlases. Independent audits confirmed micro-entrepreneurs operate from transaction records (cash, khata, inventory, sales), not coarse district population averages.
- **Decision**: Retire all geographic GIS layers, road routing, Dijkstra catchments, and policy parsing. Rebuild ArthLens exclusively as a Business Operating System with Khata, Invoicing, Purchases, Cash positions, Operational Goals, Financial Intelligence, and Decision Simulation.
- **Consequences**: Legacy geographic endpoints (`/geo/*`, `/indicators/*`, `/scenarios/*`, `/runs/*`) and dependencies (`maplibre-gl`, `pmtiles`, `cytoscape`, `networkx`, `geoalchemy2`) are removed.

### ADR-002: Pure Deterministic Arithmetic for Financial & Decision Calculations
- **Status**: `ACCEPTED`
- **Context**: Large language models cannot reliably perform accounting arithmetic or multi-period discounting. Hallucinated numbers destroy trust.
- **Decision**: Financial and decision metrics are computed in Python rather than delegated to the LLM. The eight decision evaluators and loan amortization schedule now use Decimal internally; decision result fields are rounded with `ROUND_HALF_UP` and converted to JSON numeric values at serialization. Public result contracts still expose numeric values, so end-to-end sub-cent input retention is not guaranteed. This ADR does not establish that every formula, assumption, or provenance path has been financially verified.
- **Consequences**: LLMs are restricted to plan generation, information synthesis, and narrative explanation.

### ADR-003: Domain-Driven Design & Strict Aggregate Boundaries
- **Status**: `ACCEPTED`
- **Context**: Transaction integrity requires strong aggregate invariants across businesses, customers, suppliers, products, invoices, purchases, payments, and goals.
- **Decision**: Define pure immutable Python dataclasses with rich domain invariants in `backend.arthlens.domain.business`. Maintain zero framework dependencies in the domain layer. All mutations occur through explicit repository interfaces and application services.

### ADR-004: Multi-Tenant Isolation with Request-Authorized Execution Context
- **Status**: `ACCEPTED`
- **Context**: Multi-business platforms risk horizontal privilege escalation (IDOR) where User A accesses or modifies User B's business records.
- **Decision**: Derive `user_id` strictly from authenticated JWT cookie/bearer tokens. Enforce tenant scope across every REST endpoint and repository query. Require explicit membership verification before performing business operations.

### ADR-005: Typed Decision Evaluation Graph with Multi-Alternative Ranking
- **Status**: `ACCEPTED`
- **Context**: Business decisions (e.g. equipment purchase, hiring, expansion, vendor switching) have interlinked financial dependencies and constraints.
- **Decision**: Model decisions as typed directed acyclic graphs (DAGs) comprising `INPUT`, `ASSUMPTION`, `CONSTRAINT`, `CALCULATION`, and `OUTCOME` nodes. Evaluate alternatives side-by-side using deterministic criteria, net present value, ROI, and payback period, and rank them objectively.

### ADR-006: Agentic AI Co-pilot with Strictly Bound Tenant Execution Context
- **Status**: `ACCEPTED`
- **Context**: LLM agent tools can be manipulated by malicious prompt injection to query records of unauthorized businesses.
- **Decision**: Pass a non-overridable `AgentExecutionContext` (containing authenticated `user_id`, `business_id`, and `user_roles`) into the agent runner and every tool invocation. Disallow the LLM from supplying or overriding tenant identifiers.

### ADR-007: PostgreSQL 16 Storage with Preserved Migration Lineage
- **Status**: `ACCEPTED`
- **Context**: Clean codebase evolution must preserve historical migration integrity (versions `001` through `015`) to prevent database schema drift.
- **Decision**: Retain all applied Alembic migrations without deletion or historical mutation. Business OS entities and newer finance, membership, and inventory-cost changes are introduced with forward migrations through `018_inventory_movement_cost_basis.py`.

### ADR-008: Next.js 14 Liquid-Glass Architecture with Constellation Overview
- **Status**: `ACCEPTED`
- **Context**: Modern business operators require a clear multi-enterprise operational overview with responsive, tactile interaction.
- **Decision**: Implement a liquid-glass design system in Next.js 14 with Tailwind CSS, supporting interactive business constellations (`BusinessConstellation.tsx`), dedicated workspaces (`/workspaces/[id]`), and deep analytics views.
