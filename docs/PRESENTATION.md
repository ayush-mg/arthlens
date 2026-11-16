# Executive Presentation & Defense Deck
## ArthLens: Business Operating System & Decision Intelligence Platform

**Presentation Category:** Master's Project Defense & Executive Briefing  
**Core Equation:**  
$$\text{ArthLens} = \text{Business Operating System} + \text{Financial Intelligence} + \text{Decision Intelligence} + \text{Agentic AI}$$  
**Repository:** `C:\arthlens`  
**Date:** November 2026  

> **Draft status:** This inherited presentation contains product and verification claims that have not been fully reproduced. Slides describing test results, use-case coverage, financial outputs, or a live demo are proposals until independently verified. Use [Engineering Handover](ENGINEERING_HANDOVER.md) for current evidence and blockers.

---

## Slide 1: Title Slide
- **Title:** ARTHLENS: An Evidence-Gated Business Operating System & Decision Intelligence Platform
- **Subtitle:** Bridging Operational Truth, Deterministic Financial Solvency, and Agentic AI for Indian MSMEs
- **Presenter:** Lead Engineer / Candidate
- **Environment:** Antigravity IDE | Google Gemini 2.5 | FastAPI | PostgreSQL | Next.js 14
- *Speaker Note:* "Good morning, members of the committee. Today I present ArthLens, a platform engineered to solve the fundamental operational and decision-making challenges of micro-enterprises in India."

---

## Slide 2: The Core Problem in Indian MSMEs
- **Fragmented Truth:** Day-to-day operations are split across paper notebooks (Khata), WhatsApp chats, and ad-hoc spreadsheets.
- **Credit & Working Capital Leakage:** Oral credit terms lead to unmonitored receivables ageing, customer default, and sudden insolvency.
- **The Capital Decision Blindspot:** Critical capex investments (e.g. purchasing an ₹8 Lakh commercial rotary oven) are made on gut feeling without financial modeling or risk simulation.
- **The Generative AI Trap:** Generic AI chatbots hallucinate arithmetic, invent loan interest rates, and cannot be trusted for consequential business decisions.
- *Speaker Note:* "Over 110 million people in India depend on micro-enterprises. Yet when an entrepreneur wants to make an ₹8 lakh investment, they either guess or ask ChatGPT, which happily hallucinates math. ArthLens fixes this at the foundation."

---

## Slide 3: The ArthLens Solution & Central Equation
$$\mathbf{ArthLens = Business\ OS + Financial\ Intelligence + Decision\ Intelligence + Agentic\ AI}$$

1. **Business OS:** Everyday source of truth (Khata, WAC inventory, invoicing).
2. **Financial Intelligence:** Automatic P&L, Cash Flow, Solvency, Ageing, Health score.
3. **Decision Intelligence:** 8 versioned models, 3-alternative ranking, 1,000-path Monte Carlo risk.
4. **Agentic AI:** Gemini 2.5 formulating multi-step investigation DAGs calling 16 deterministic tools.
- *Speaker Note:* "ArthLens is not a chatbot and not just another accounting ledger. Its unique value comes from connecting live operations to deterministic financial analysis and explainable decisions."

---

## Slide 4: Central Product Philosophy
- **Records are the Source of Truth:** Every insight is grounded in immutable double-entry database records.
- **Deterministic Financial Calculations:** LLMs do not compute figures. Accounting and decision formulas use Python Decimal internally; stochastic simulations use seeded NumPy.
- **Explicit Versioned Models:** All capital decision models are versioned (v1.0.0) with declared inputs, constraints, and formulas.
- **Missing Information is Surfaced:** The system asks clarification questions rather than synthesizing guesses.
- **Evidence-Gated Action:** Recommendations are supported by mathematical lineage and downloadable audit briefs.
- *Speaker Note:* "Our philosophy is simple: never let an LLM do arithmetic, and never let evidence gating result in an empty screen."

---

## Slide 5: System Architecture (C4 Level 2)
- **Presentation Tier:** Next.js 14 App Router, Three.js 3D Business Constellation galaxy, Framer Motion fluid animations, Tailwind CSS liquid-glass aesthetic.
- **Application Tier:** FastAPI REST Gateway running Uvicorn ASGI with JWT bearer authentication and role-based access control.
- **Domain & Intelligence Engines:** Python 3.14/3.12 services executing WAC valuation, solvency ratios, NumPy PCG64 Monte Carlo, and OAT Tornado sensitivity.
- **Data Tier:** PostgreSQL 16 relational database with 16 BOS tables and Alembic migrations.
- *Speaker Note:* "Our architecture enforces strict Clean Architecture: domain entities have no dependencies on frameworks; persistence is abstracted behind 11 repositories."

---

## Slide 6: Multi-Business Workspaces & Khata Receivables
- **Multi-Tenant Workspaces:** Support for multiple isolated business workspaces per user.
- **Customer Khata (Receivables):**
  - Credit limit enforcement prevents issuing invoices when credit exposure is exceeded.
  - Credit period tracking (30/45/60 days).
  - Running balance updated automatically on invoices and collections.
- **Vendor Khata (Payables):**
  - Bill posting increments supplier payables.
  - Partial settlements tracked across cash and bank channels.
- *Speaker Note:* "In India, business is built on Khata. ArthLens gives the entrepreneur an automated, double-entry credit ledger with strict credit limit protection."

---

## Slide 7: Perpetual Inventory & Weighted Average Cost (WAC)
$$\text{WAC}_{\text{new}} = \frac{(\text{Stock}_{\text{prev}} \times \text{Cost}_{\text{prev}}) + (\text{Qty}_{\text{new}} \times \text{Price}_{\text{new}})}{\text{Stock}_{\text{prev}} + \text{Qty}_{\text{new}}}$$

- **Perpetual Tracking:** Real-time stock counts on every inward and outward movement.
- **Dynamic Revaluation:** Cost-of-Goods-Sold (COGS) reflects true weighted procurement cost.
- **Stock Decrement Integration:** Invoices automatically deduct inventory stock and record immutable movement logs.
- **Reorder Threshold Alerts:** Visual alerts when inventory drops below safety levels.
- *Speaker Note:* "If flour prices double and an entrepreneur prices bread based on last month's purchase, they lose money on every loaf sold. Our perpetual WAC engine ensures COGS is always accurate."

---

## Slide 8: Deterministic Financial Intelligence Suite
- **Profit & Loss Statement:** Gross sales, derived COGS, gross margin %, OPEX categories, EBITDA, and net profit before tax.
- **Multi-Stream Cash Flow:** Reconciles operating inflows/outflows, investing asset purchases, and financing debt movements.
- **Solvency & Working Capital:**
  - Current Ratio ($\text{Current Assets} / \text{Current Liabilities}$)
  - Quick Ratio ($\text{Acid Test}$)
  - Solvency Classification: STRONG, ADEQUATE, STRESSED, INSOLVENT.
- **90-Day Ageing Buckets:** Visual partitioning into 0-30, 31-60, 61-90, and 90+ days.
- **5-Pillar Health Score:** Composite 0-100 rating with identified operational strengths and vulnerabilities.
- *Speaker Note:* "Entrepreneurs do not need a 40-page ledger dump. They need instant clarity: Am I solvent? Which customers owe me past 60 days? What is my break-even cushion?"

---

## Slide 9: The Decision Laboratory (8 Versioned Models)
1. **Machine / Equipment Purchase** (The Flagship ₹8L Rotary Oven Journey)
2. **New Product Line Addition**
3. **Supplier Switch or Credit Terms**
4. **Bulk Discount vs. Storage Cost**
5. **New Branch / Location Opening**
6. **Hiring Staff or Commission Structure**
7. **Credit Term Extension to Customer**
8. **Price Increase vs. Demand Elasticity**
- *Speaker Note:* "Every model is versioned (v1.0.0). When an entrepreneur evaluates a decision, the model pre-populates live baseline figures from their database."

---

## Slide 10: 3-Alternative Strategic Ranking
For every capital decision, the engine evaluates and ranks three alternatives:
- **Alternative 1 (Recommended):** Bank Financed Loan (e.g. 36 months @ 10.5%).
- **Alternative 2 (Conservative / Self-Financed):** Outright Cash Purchase.
- **Alternative 3 (Status Quo):** Do Nothing / Maintain Existing Operations.
- **Evaluation Metrics:**
  - Net Present Value (NPV)
  - Internal Rate of Return (IRR)
  - Payback Period (Months)
  - Monthly Net Cash Flow Impact
  - Debt Service Coverage Ratio (DSCR)
  - Outcome Badge: `HIGHLY_RECOMMENDED`, `FEASIBLE`, `CAUTION_HIGH_RISK`, `NOT_VIABLE`.
- *Speaker Note:* "Notice that self-financing the entire ₹8 lakhs in cash triggers CAUTION_HIGH_RISK because it drains the business's liquid cash below the ₹1 lakh emergency floor. Loan financing is ranked #1 with a 2.88x DSCR."

---

## Slide 11: 1,000-Path Monte Carlo Risk Simulation
- **Engine:** NumPy `PCG64` (64-bit Permuted Congruential Generator).
- **Stochastic Variables:** Incremental sales volume ($\pm 15\%$), variable material costs ($\pm 10\%$).
- **Output Percentiles:**
  - **P10 (Worst Case):** Downside safety floor.
  - **P50 (Median):** Expected operational trajectory.
  - **P90 (Best Case):** Upside growth ceiling.
- **Risk Metrics:** Downside shortfall probability ($\le 5.0\%$) and Value-at-Risk ($VaR_{95\%}$).
- *Speaker Note:* "We don't just calculate a single NPV. We simulate 1,000 potential futures to tell the business owner: 'There is only a 3.8% chance this investment loses money.'"

---

## Slide 12: One-At-A-Time (OAT) Sensitivity Tornado Chart
- **Methodology:** Varies each parameter by $\pm 20\%$ while holding all others constant.
- **Elasticity Formulation:**
  $$\text{Elasticity} = \frac{\% \Delta \text{Net Monthly Cash Impact}}{\% \Delta \text{Input Parameter}}$$
- **Visual Presentation:** Interactive horizontal Tornado swings ordered by risk magnitude.
- **Actionable Insight:** Identifies the Primary Risk Driver (e.g., Capacity Sales Volume).
- *Speaker Note:* "The Tornado chart shows the entrepreneur exactly where to focus their attention: If sales volume drops by 20%, cash flow drops by ₹18,000; but if maintenance doubles, cash flow only drops by ₹4,000."

---

## Slide 13: Agentic Gemini AI Copilot Architecture
- **Provider:** Google Gemini 2.5 with autonomous fallback DAG planner.
- **CredentialFirewall:** Strips API keys, passwords, and tokens before LLM dispatch.
- **16-Tool Registry:** Pydantic-validated tools for querying cash, ledgers, inventory, and evaluating decision models.
- **Zero-Hallucination Policy:** Gemini is strictly forbidden from doing math. It generates DAG investigation plans and synthesizes explanations using tool outputs only.
- **Data Gap Identification:** When critical facts are missing, the copilot formulates specific follow-up questions for the owner.
- *Speaker Note:* "Gemini acts as an investigative analyst, not a calculator. It decides which tools to call, inspects the evidence, and explains the results in plain language."

---

## Slide 14: Governance & Reporting Engine
- **2-Page Executive Decision Brief (PDF):**
  - Page 1: Decision context, baseline financials, 3-alternative ranking table, outcome verdict.
  - Page 2: Monte Carlo risk distribution, DSCR analysis, repayment schedule, signature block.
- **Complete Business Dossier (PDF):** Multi-section report compiling business profile, P&L, balance sheet, solvency ratios, and ageing buckets.
- **CSV Ledger Exports:** Downloadable customer and supplier ledgers with OWASP formula injection sanitization.
- *Speaker Note:* "The 2-page decision brief is formatted specifically for Indian banks. An entrepreneur can take this directly to a bank manager to secure a MUDRA loan."

---

## Slide 15: Motion-Led UI: Business Constellation 3D
- **Visual Language:** Liquid-glass aesthetic with backdrop blurs and editorial typography.
- **Business Constellation 3D:**
  - Interactive Three.js WebGL canvas rendering business workspaces as glowing stars.
  - Orbiting mini-satellites for Khata, Inventory, Cash, and Decisions.
  - Node glow reflects health score: Emerald (Healthy), Amber (Attention), Crimson (Critical).
  - Raycaster mouse picking with holographic HUD tooltips and one-click workspace navigation.
- *Speaker Note:* "Instead of boring accounting lists, business owners see their enterprise as an interactive constellation of operational units."

---

## Slide 16: Verification & Test Results
- **Observed frontend tests:** 19 passed across 3 files in the current review.
- **Observed backend pure tests:** 27 passed with the database fixture bypassed; integration behavior remains unverified.
- **Browser E2E:** 2 tests passed for the auth lifecycle and cross-tenant IDOR; broader operational journeys remain unverified.
- **Build:** Next.js production build completed successfully in the current review.
- **Requirements coverage:** Not verified row by row; see the candidate traceability matrix and engineering handover.
- *Speaker Note:* Replace this slide with captured CI and end-to-end results before presenting release readiness.

---

## Slide 17: Case Study Walkthrough: The ₹8 Lakh Rotary Oven
1. **The Scenario:** An illustrative equipment purchase whose business records and loan terms must be supplied explicitly.
2. **The Question:** Can the business afford the purchase and financing while preserving its required cash reserve?
3. **The Evidence:** Use only verified business records and explicit user-supplied assumptions.
4. **The Agent Investigation:** Show the plan, missing inputs, deterministic calculation outputs, and their provenance from an actual run.
5. **The Result:** Insert a screenshot and values captured from a verified E2E session; do not use inherited example figures.
6. **The Deliverable:** Confirm the decision brief PDF from that same run before presenting it as available.
- *Speaker Note:* Replace this template with an observed journey and current outputs from the target environment.

---

## Slide 18: Software Engineering Rigor
- **IEEE 830 SRS:** Full requirements specification in `docs/SRS.md`.
- **C4 Architecture:** Context, Container, Component, and Code diagrams in `docs/ARCHITECTURE.md`.
- **SOLID & 23 Design Patterns:** Formal mapping in `docs/OOM_DESIGN.md`.
- **Requirements Traceability Matrix (RTM):** 100 use cases traced to tests in `docs/REQUIREMENTS_TRACEABILITY.md`.
- **Test Evidence:** Documented test execution tables in `docs/TEST_PLAN_AND_RESULTS.md`.
- *Speaker Note:* "We treat micro-enterprise software with the same engineering rigor as high-frequency trading platforms. Documentation, traceability, and architectural integrity are preserved."

---

## Slide 19: Socio-Economic Impact
- **Democratizing Financial Intelligence:** Gives micro-entrepreneurs the financial tools previously reserved for large corporate enterprises.
- **Access to Formal Banking:** Institutional-grade PDF dossiers replace informal loan applications, unlocking low-interest MUDRA and CGTMSE government credit.
- **Preventing Insolvency:** WAC valuation and credit limit gates prevent the cash flow crises that kill 60% of small businesses within their first 3 years.
- *Speaker Note:* "Technology has the power to transform lives. ArthLens empowers the micro-entrepreneur to move from survival book-keeping to confident, evidence-based business growth."

---

## Slide 20: Conclusion & Q&A
- **Summary:**
  - $\text{ArthLens} = \text{Business OS} + \text{Financial Intelligence} + \text{Decision Intelligence} + \text{Agentic AI}$.
  - Product implementation and acceptance remain in progress.
  - Current observed checks and unresolved gates are listed in `docs/ENGINEERING_HANDOVER.md`.
- **Live System Demo:** Rehearse and verify against a clean migrated environment before presenting.
- **Thank you! Questions & Discussion.**
- *Speaker Note:* Present only results reproduced in the target demo environment.
