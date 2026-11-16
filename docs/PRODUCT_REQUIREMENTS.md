# ArthLens Product Requirements Document (PRD)

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform  
**Target Release:** 1.0 Production Readiness  
**Equation:** $$\text{ArthLens} = \text{Business Operating System} + \text{Financial Intelligence} + \text{Decision Intelligence} + \text{Agentic AI}$$

---

## 1. Functional Requirements

### 1.1 Multi-Business Operating System (BOS)
- **FR-BOS-01 Workspace Management**: Users can register and operate multiple businesses (workspaces) under a single authenticated account.
- **FR-BOS-02 Customer Khata**: Manage customer directory, credit limits, opening balances, transaction records, and real-time receivables ledger.
- **FR-BOS-03 Supplier Khata**: Manage supplier directory, payment terms, opening balances, purchase obligations, and payables ledger.
- **FR-BOS-04 Product Catalog & Inventory**: Register products with SKU, unit pricing, GST rates, minimum stock thresholds, inventory movements, and reorder alerts.
- **FR-BOS-05 Sales Invoicing**: Issue, fulfill, and track multi-item sales invoices with automatic tax, discount, inventory decrement, and customer khata adjustment.
- **FR-BOS-06 Purchase Orders**: Create, verify, and complete supplier purchase orders with inventory increment and accounts payable ledger tracking.
- **FR-BOS-07 Cash & Payment Flow**: Record real-time cash, UPI, bank, and credit payments with atomic double-entry verification.
- **FR-BOS-08 Operational Goals**: Define target revenue, cash buffer, margin, and cost goals with progress tracking and status indicators.

### 1.2 Financial Intelligence Engine (FIE)
- **FR-FIE-01 Profit & Loss Statement**: Deterministic calculation of gross revenue, COGS, operating expenses, taxes, and net profit over configurable date ranges.
- **FR-FIE-02 Cash Flow Statement**: Decomposition of cash flows into operating, investing, and financing activities.
- **FR-FIE-03 Working Capital Analysis**: Real-time evaluation of operating cycle, cash conversion cycle, and working capital sufficiency.
- **FR-FIE-04 Ageing Analysis**: Categorization of accounts receivable and accounts payable into 0-30, 31-60, 61-90, and 90+ day buckets.
- **FR-FIE-05 Break-Even Analysis**: Calculation of fixed costs, weighted contribution margins, break-even unit sales, and revenue targets.
- **FR-FIE-06 Business Health Score**: Deterministic composite scoring (0-100) across liquidity, profitability, debt coverage, and operational efficiency.

### 1.3 Decision Intelligence Engine (DIE)
- **FR-DIE-01 Typed Decision Graphs**: Structure consequential business choices (equipment purchase, hiring, expansion, vendor switching) into typed DAGs with input, assumption, constraint, calculation, and outcome nodes.
- **FR-DIE-02 Alternative Evaluation**: Generate and compare mutually exclusive alternatives side-by-side using NPV, payback period, and ROI.
- **FR-DIE-03 Constraint Enforcement**: Verify that alternatives do not violate hard operational constraints (e.g. minimum cash reserves, maximum debt service).
- **FR-DIE-04 Monte Carlo Risk Simulation**: Run deterministic pseudo-random Monte Carlo simulations with explicit seeds to generate outcome probability distributions.
- **FR-DIE-05 Sensitivity Analysis**: Perform one-at-a-time parameter perturbation to identify the key driver variables affecting decision viability.
- **FR-DIE-06 Decision Audit Trails**: Persist full decision snapshots with inputs, models, alternative evaluations, and chosen options.

### 1.4 Agentic AI Co-pilot (AAI)
- **FR-AAI-01 Objective Interpretation**: Google Gemini parses natural language queries and business objectives into structured multi-step plans.
- **FR-AAI-02 Governed Tool Execution**: Execute deterministic application tools to query khata balances, check inventory, evaluate margins, and run simulations.
- **FR-AAI-03 Tenant-Enforced Execution**: Strictly bind tool execution context to the authenticated user and authorized workspace.
- **FR-AAI-04 Missing Fact Surfacing**: Refuse to guess missing financial records; explicitly prompt the operator for missing assumptions.
- **FR-AAI-05 Multi-Format Reports**: Synthesize verified business findings into clear JSON, summary metrics, and narrative executive briefings.

---

## 2. Non-Functional Requirements

- **NFR-SEC-01 Authentication**: Argon2id password hashing, HTTP-only secure JWT cookies, single-use password reset tokens, and real-time role revocation.
- **NFR-SEC-02 Tenant Isolation**: Absolute horizontal privilege separation (zero IDOR vulnerability across multi-tenant workspaces).
- **NFR-PERF-01 Latency**: Financial ratio queries compute deterministically in $< 50\text{ ms}$; full business dashboards render in $< 200\text{ ms}$.
- **NFR-REL-01 Fail-Closed Logic**: Any network or LLM failure automatically falls back to deterministic rule evaluations without data corruption.
- **NFR-AUD-01 Immutability**: All payment transactions, ledger entries, and decision audits maintain immutable audit history.
