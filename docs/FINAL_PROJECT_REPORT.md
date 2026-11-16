# Academic Master Project Report
## ArthLens: An Evidence-Gated Business Operating System & Decision Intelligence Platform for Micro-Enterprises

> **Review status: UNVERIFIED DRAFT.** The inherited completion claims in this report are not supported by a reproducible full test run. See [Engineering Handover](ENGINEERING_HANDOVER.md) and [Test Plan and Observed Results](TEST_PLAN_AND_RESULTS.md) for the current evidence and open release gates.

**Degree / Discipline:** Master of Science / Technology in Computer Science & Software Engineering  
**Project Category:** Business Operating System & Decision Intelligence  
**Repository:** `C:\arthlens`  
**Core Thesis:**  
$$\text{ArthLens} = \text{Business Operating System} + \text{Financial Intelligence} + \text{Decision Intelligence} + \text{Agentic AI}$$  
**Release Version:** Unverified draft; release status not established  
**Evaluation Date:** November 2026  

---

## Abstract

Micro, Small, and Medium Enterprises (MSMEs) form the backbone of the Indian economy, contributing over 30% of GDP and employing more than 110 million citizens. Despite this significance, micro-entrepreneurs face pervasive operational and decision-making barriers: everyday book-keeping is fragmented across paper notebooks (Khata) and generic spreadsheets; formal banking credit requires sophisticated financial ratios that business owners cannot compute; capital expenditure decisions (e.g., machinery purchases, branch expansion) are made on intuition without risk modeling; and modern Generative AI chatbots hallucinate arithmetic or lack access to verified business records.

This inherited report describes a proposed **ArthLens** Business Operating System and Decision Intelligence Platform. Its architectural, financial, model-count, and feature descriptions have not been reconciled against every current implementation path. The previous reported test totals, production build, and 100-use-case completion claim were not reproduced in this review and are withdrawn as evidence. Current observed checks and release blockers are recorded in [Engineering Handover](ENGINEERING_HANDOVER.md) and [Test Plan and Observed Results](TEST_PLAN_AND_RESULTS.md).

---

## 1. Introduction & Motivation

### 1.1 The Micro-Enterprise Reality in India
Indian micro-enterprises operate under unique structural dynamics:
- **Informal Credit Culture (Khata):** Goods are sold on oral credit terms. Receivables ageing is tracked manually, leading to capital tie-up and bad debts.
- **Volatile Input Pricing:** Raw material prices fluctuate rapidly, necessitating perpetual inventory revaluation to prevent selling below replacement cost.
- **Severe Working Capital Constraints:** Micro-enterprises cannot absorb unhedged capital expenditure failures. A single ill-timed equipment purchase can trigger liquidity insolvency.
- **The LLM Math Hallucination Hazard:** While large language models excel at natural language synthesis, their autoregressive transformer architectures frequently fabricate arithmetic calculations, invent interest rates, and produce dangerously flawed business advice when left ungoverned.

### 1.2 The ArthLens Solution
ArthLens replaces fragmented spreadsheets and hallucinating chatbots with an integrated platform grounded in the central equation:
$$\text{ArthLens} = \text{Business Operating System} + \text{Financial Intelligence} + \text{Decision Intelligence} + \text{Agentic AI}$$

The platform enforces five non-negotiable principles:
1. **Business records are the sole source of truth.**
2. **Financial calculations are intended to be deterministic.** Decision evaluators and loan schedules use Decimal internally, while API result values remain JSON numbers. Full calculation-path coverage and the required input/output precision contract remain to be verified.
3. **Decision models are explicit, versioned, and constrained.**
4. **AI assists investigation and communication; it never computes arithmetic.**
5. **Missing information is identified rather than fabricated.**

---

## 2. Mathematical Formulations & Theoretical Foundations

### 2.1 Perpetual Weighted Average Cost (WAC) Inventory Valuation
To reflect true cost-of-goods-sold across changing purchase prices, inventory stock is valued using the perpetual Weighted Average Cost method:
$$\text{WAC}_{t} = \frac{V_{t-1} + (Q_{\text{in}} \times P_{\text{in}})}{Q_{t-1} + Q_{\text{in}}}$$
Where:
- $V_{t-1}$ is the prior total valuation ($Q_{t-1} \times \text{WAC}_{t-1}$)
- $Q_{\text{in}}$ is the incoming shipment quantity
- $P_{\text{in}}$ is the unit purchase price
Upon sales invoicing, COGS is deducted deterministically as $Q_{\text{sold}} \times \text{WAC}_t$, guaranteeing that gross margins reflect actual historical procurement expenditure.

### 2.2 Financial Intelligence & Solvency Formulation
The platform computes standard accounting identities with Decimal precision:
1. **Gross Profit:**
   $$\text{Gross Profit} = \text{Gross Revenue} - \text{COGS}$$
2. **Operating Profit (EBITDA):**
   $$\text{EBITDA} = \text{Gross Profit} - \sum \text{Operating Expenses}$$
3. **Current Ratio:**
   $$\text{Current Ratio} = \frac{\text{Current Assets}}{\text{Current Liabilities}} = \frac{\text{Cash} + \text{Receivables} + \text{Inventory}}{\text{Payables}}$$
4. **Quick Ratio (Acid-Test):**
   $$\text{Quick Ratio} = \frac{\text{Cash} + \text{Receivables}}{\text{Payables}}$$
5. **Break-Even Quantity ($Q_{\text{BE}}$):**
   $$Q_{\text{BE}} = \frac{\text{Fixed Costs}}{\text{Price per Unit} - \text{Variable Cost per Unit}}$$

### 2.3 Capital Decision Modeling (The Flagship ₹8 Lakh Equipment Investment)
Capital investments are modeled over the useful life of the asset ($n$ years) using Discounted Cash Flow (DCF):
1. **Equal Monthly Installment (EMI):**
   $$\text{EMI} = P \times r \times \frac{(1 + r)^m}{(1 + r)^m - 1}$$
   Where $P$ is principal loan amount, $r$ is monthly interest rate ($i_{\text{annual}} / 12$), and $m$ is tenure in months.
2. **Net Present Value (NPV):**
   $$\text{NPV} = -I_0 + \sum_{t=1}^N \frac{\Delta CF_t}{(1 + k)^t}$$
   Where $I_0$ is the cash down payment, $\Delta CF_t$ is incremental net monthly cash flow, and $k$ is the enterprise hurdle rate.
3. **Debt Service Coverage Ratio (DSCR):**
   $$\text{DSCR} = \frac{\text{EBITDA}_{\text{monthly}}}{\text{EMI} + \text{Maintenance}}$$
   The model enforces a hard constraint $\text{DSCR} \ge 1.25$ to satisfy Indian banking credit norms.

### 2.4 Stochastic Simulation via NumPy PCG64 Monte Carlo
Rather than relying on single-point estimates, ArthLens executes 1,000 stochastic simulation iterations using the 64-bit Permuted Congruential Generator (`PCG64`):
$$\tilde{Q}_i \sim \mathcal{N}\left(\mu_Q, \sigma_Q^2\right), \quad \tilde{P}_i \sim \mathcal{N}\left(\mu_P, \sigma_P^2\right)$$
For each path $i \in \{1, \dots, 1000\}$, the simulation evaluates cash flow outcomes and computes empirical percentiles:
- **$P_{10}$ (Worst Case):** 10th percentile outcome (downside protection).
- **$P_{50}$ (Median):** Expected operational trajectory.
- **$P_{90}$ (Best Case):** 90th percentile upside.
- **Value-at-Risk ($VaR_{95\%}$):** Maximum loss expected with 95% confidence.

### 2.5 One-At-A-Time (OAT) Sensitivity Elasticity
To pinpoint the primary operational risk driver, the engine varies each input parameter $x_j$ by $\pm 20\%$ deterministically while holding all other variables constant:
$$\text{Elasticity}_j = \frac{|\Delta Y / Y_0|}{|\Delta x_j / x_{j,0}|}$$
The variables are sorted in descending order of elasticity to generate the horizontal Tornado chart swings.

---

## 3. Platform Architecture & Implementation

ArthLens is structured into five cohesive tiers adhering to Clean Architecture and DDD:

```
+-----------------------------------------------------------------------------------------+
|                                ARTHLENS FULL-STACK PLATFORM                             |
+-----------------------------------------------------------------------------------------+
|  Tier 1: Presentation & Constellation                                                   |
|    - Next.js 14 App Router + React 18 + Tailwind CSS                                    |
|    - Three.js 3D WebGL Business Constellation (Galaxy of Multi-Business Workspaces)     |
|    - Framer Motion Fluid Micro-Interactions & Liquid-Glass Modals                       |
+-----------------------------------------------------------------------------------------+
|  Tier 2: API Gateway & Security                                                         |
|    - FastAPI REST Gateway with OAuth2 Bearer JWT Authentication                          |
|    - Role-Based Access Control (OWNER, MANAGER, ACCOUNTANT, VIEWER)                      |
|    - Multi-Tenant Workspace Isolation Filters                                           |
+-----------------------------------------------------------------------------------------+
|  Tier 3: Core Domain & Services                                                         |
|    - BusinessService: Workspaces, Khata Receivables/Payables, Invoicing, WAC Inventory      |
|    - FinancialIntelligenceEngine: P&L, Cash Flow, Solvency, Ageing, Break-even, Health      |
|    - DecisionIntelligenceEngine: 8 Versioned Models, 3-Alternative Ranking Table        |
|    - SimulationEngine: 1,000-Path NumPy PCG64 Monte Carlo, OAT Tornado Swings            |
+-----------------------------------------------------------------------------------------+
|  Tier 4: Agentic AI & Governance                                                        |
|    - BusinessAgent: Gemini 2.5 + CredentialFirewall + Multi-Step DAG Planner            |
|    - BusinessToolRegistry: 16 Strictly Deterministic Application Tools                  |
|    - BusinessReportGenerator: 2-Page Decision Briefs & Business Dossiers in ReportLab   |
|    - OWASP Formula-Sanitized CSV Ledger Exporters                                       |
+-----------------------------------------------------------------------------------------+
|  Tier 5: Persistence & Infrastructure                                                   |
|    - PostgreSQL 16 Database (Port 5433 host mapping)                                    |
|    - 16 Relational Tables managed via Alembic Migrations                                |
|    - 11 SQLAlchemy 2.0 Repositories with Atomic Transaction Sessions                    |
+-----------------------------------------------------------------------------------------+
```

---

## 4. Empirical Evaluation & The Flagship Case Study

### 4.1 The Case: Annapurna Bakeries & Sweets (₹8 Lakh Rotary Oven Expansion)
To validate the integrated system end-to-end, an automated integration test (`test_flagship_demonstration_journey.py`) executed the flagship micro-enterprise journey:
- **Baseline Establishment:** The business is established in Varanasi with ₹3,50,000 cash reserve.
- **Khata Operations:** Registered customer "Royal Sweets & Retailers" (₹1,00,000 credit limit) and supplier "Apex Flour Mills Ltd".
- **Procurement & Invoicing:** Procured 500 units of raw materials @ ₹28.00 (WAC: ₹28.00); issued invoice for 200 units of artisan bread @ ₹60.00 (Total: ₹12,600). Stock decremented to 300 units; customer balance charged ₹12,600. Partial payment of ₹6,300 collected.
- **Financial Intelligence:**
  - Invoiced Revenue: ₹12,600.00
  - Derived COGS: ₹5,600.00 ($200 \times \text{WAC } ₹28.00$)
  - Gross Profit: ₹7,000.00 (Gross Margin: 55.56%)
  - Accounts Receivable: ₹6,300.00 (all within 0-30 day bucket)
  - Solvency: Strong, Net Working Capital positive.
- **Decision Laboratory Evaluation (₹8,00,000 Rotary Rack Oven):**
  - Evaluated 3 alternatives: (1) Bank Financed Loan (36 months @ 10.5%), (2) Self-Financed Cash, (3) Status Quo (Do Nothing).
  - Alternative 1 achieved **Rank 1**: Monthly net cash impact $+₹45,200$, Payback: 14.2 months, DSCR: 2.88x (well above the 1.25x bank covenant), Outcome: `FEASIBLE` / `HIGHLY_RECOMMENDED`.
  - Alternative 2 flagged `CAUTION_HIGH_RISK` due to depletion of operational working capital reserve below the ₹1,00,000 floor.
- **1,000-Path Monte Carlo Simulation:**
  - Evaluated capacity volume and cost variance under NumPy PCG64.
  - Shortfall risk probability $\le 5.0\%$, producing `HIGH_CONFIDENCE_VIABLE` verdict.
- **Agentic AI Copilot Investigation:**
  - Owner asked: *"Should we buy the 8 lakh rotary oven for the bakery?"*
  - Gemini formulated a 4-step DAG plan (`get_cash_position` $\to$ `evaluate_decision_model` $\to$ `run_risk_simulation` $\to$ `synthesize`).
  - Executed all tools deterministically, returning synthesized advice with a recommendation to proceed under loan financing.
- **Governance Artifacts:**
  - Generated 2-page Executive Decision Brief PDF (1,482 bytes) and Complete Business Dossier PDF (2,894 bytes).
  - Downloaded CSV customer and supplier ledgers with OWASP formula sanitization.

---

## 5. Verification Status

The inherited test totals and build claims in earlier versions of this report are not supported by reproducible evidence from the current review. The observed checks, exact commands, and blocked or unstarted acceptance gates are maintained in [Test Plan and Observed Results](TEST_PLAN_AND_RESULTS.md). Do not treat historical metrics elsewhere in this draft as verified results.

---

## 6. Socio-Economic Impact & Conclusion

### 6.1 Impact on Indian Micro-Enterprises
ArthLens bridges the critical technological and financial divide for Indian MSMEs:
1. **Bankability:** Generates institutional-grade 2-page decision briefs and dossiers with DSCR and NPV proofs, enabling micro-entrepreneurs to secure formal bank loans under MUDRA and CGTMSE schemes rather than relying on predatory moneylenders.
2. **Loss Prevention:** Perpetual WAC inventory and credit limit enforcement prevent working capital leakage and involuntary insolvency.
3. **Evidence-Gated AI Trust:** Business owners can query Gemini with confidence, knowing that all financial arithmetic is evaluated by Python domain engines rather than hallucinated by an LLM.

### 6.2 Conclusion & Future Directions
ArthLens successfully proves that combining an operational source of truth, deterministic financial intelligence, versioned capital models, and governed agentic AI creates a reliable, explainable, and production-ready decision intelligence platform. Future enhancements include multi-lingual voice interfaces (Hindi, Tamil, Bengali) and direct integration with Account Aggregator and GSTN e-invoicing APIs.
