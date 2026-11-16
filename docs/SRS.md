# Software Requirements Specification (SRS)
## ArthLens: Business Operating System & Decision Intelligence Platform

**Document Standard:** IEEE Std 830-1998  
**Project:** ArthLens  
**Repository:** `C:\arthlens`  
**Core Equation:** `ArthLens = Business Operating System + Financial Intelligence + Decision Intelligence + Agentic AI`  
**Version:** 2.0.0-RELEASE  
**Date:** November 2026  

---

## 1. Introduction

### 1.1 Purpose
This document specifies the software requirements for ArthLens, an enterprise-grade business management and decision-support platform designed for Indian micro-, small-, and medium-sized enterprises (MSMEs). ArthLens integrates a deterministic operational source of truth (Business OS), an automated financial statement and solvency analysis engine (Financial Intelligence), a versioned multi-alternative simulation lab (Decision Intelligence), and an agentic AI copilot (powered by Google Gemini 2.5) that executes strict zero-hallucination deterministic tools.

### 1.2 Scope
ArthLens encompasses 100 verified functional use cases (UC-01 through UC-100) across 12 distinct architectural modules:
1. **Multi-Business Workspaces & Identity** (UC-01 to UC-08)
2. **Khata & Customer Receivables** (UC-09 to UC-16)
3. **Vendor Payables & Procurement** (UC-17 to UC-24)
4. **Perpetual Inventory & WAC Valuation** (UC-25 to UC-32)
5. **Sales Invoicing & Stock Integration** (UC-33 to UC-40)
6. **Purchases & Bill Settlements** (UC-41 to UC-48)
7. **Cash Position & Operational Goals** (UC-49 to UC-56)
8. **Deterministic Financial Intelligence** (UC-57 to UC-64)
9. **Decision Laboratory & Versioned Models** (UC-65 to UC-72)
10. **Monte Carlo & Sensitivity Simulation** (UC-73 to UC-80)
11. **Agentic Gemini Copilot & Tool DAG** (UC-81 to UC-90)
12. **Reporting, Governance & Audit Trails** (UC-91 to UC-100)

### 1.3 Definitions, Acronyms, and Abbreviations
- **WAC:** Weighted Average Cost perpetual inventory valuation.
- **DSCR:** Debt Service Coverage Ratio ($EBITDA / \text{Annual Debt Service}$).
- **NPV:** Net Present Value ($\sum_{t=0}^n \frac{CF_t}{(1 + r)^t}$).
- **IRR:** Internal Rate of Return ($NPV = 0$).
- **OAT:** One-At-A-Time sensitivity elasticity analysis.
- **PCG64:** Permuted Congruential Generator 64-bit random number generator.
- **DAG:** Directed Acyclic Graph.
- **Khata:** Traditional Indian credit ledger recording customer dues (receivables) and vendor commitments (payables).

---

## 2. Overall Description

### 2.1 Product Perspective
ArthLens operates as a self-contained, multi-tenant web application.
- **Backend:** FastAPI (Python 3.12/3.14), SQLAlchemy 2.0 ORM, PostgreSQL with Psycopg 3.
- **Frontend:** Next.js 14 (App Router), React 18, Three.js (WebGL Business Constellation 3D galaxy), Framer Motion, Tailwind CSS.
- **Reporting:** ReportLab PDF Generation engine, OWASP formula-sanitized CSV exports.
- **AI Copilot:** Google Gemini Interactions API with local fallback deterministic DAG planners.

```
+-----------------------------------------------------------------------------------------+
|                                ARTHLENS PLATFORM ARCHITECTURE                           |
+-----------------------------------------------------------------------------------------+
|  Presentation:  Next.js 14 App Router + Three.js 3D Constellation + Framer Motion      |
+-----------------------------------------------------------------------------------------+
|  API Gateway:   FastAPI REST Endpoints + JWT OAuth2 Bearer Authentication + RBAC        |
+-----------------------------------------------------------------------------------------+
|  Domain Logic:  1. Business Operating System (Workspaces, Khata, Inventory WAC, Sales)  |
|                 2. Financial Intelligence Engine (P&L, Cash Flow, Solvency, Ageing)     |
|                 3. Decision Laboratory (8 Versioned Models, 3-Alternative Ranking)      |
|                 4. Simulation Engine (1,000-path PCG64 Monte Carlo, OAT Tornado Swings) |
|                 5. Agentic AI Layer (Gemini 2.5 + 16 Deterministic Application Tools)   |
|                 6. Governance Engine (ReportLab PDF Briefs, Complete Dossiers, CSV)     |
+-----------------------------------------------------------------------------------------+
|  Persistence:   PostgreSQL Relational DB (16 BOS Tables + Alembic Versioned Migrations) |
+-----------------------------------------------------------------------------------------+
```

### 2.2 User Characteristics
- **Business Owner:** Primary entrepreneur with full workspace ownership, financial visibility, capital decision rights, and dossier generation privileges.
- **Manager:** Operational administrator capable of issuing invoices, receiving purchase shipments, adjusting stock, and querying the copilot.
- **Accountant:** Financial officer managing party ledgers, reconciling collections, and auditing tax schedules.
- **Viewer / Auditor:** Read-only stakeholder inspecting reports, historical evaluations, and compliance records.

---

## 3. Specific Functional Requirements (100 Use Cases)

### Module 1: Multi-Business Workspaces & Identity (UC-01 to UC-08)
- **FR-01 (UC-01): Workspace Creation:** System shall allow users to instantiate multiple enterprise workspaces with isolated ledgers, charts of accounts, and financial years.
- **FR-02 (UC-02): Workspace Switching:** System shall support seamless switching between workspaces with state isolation.
- **FR-03 (UC-03): Role-Based Access Control:** System shall enforce OWNER, MANAGER, ACCOUNTANT, and VIEWER roles per workspace.
- **FR-04 (UC-04): Member Invitation:** Owners shall invite members via email with explicit role assignment.
- **FR-05 (UC-05): Member Revocation:** System shall allow removing members and revoking workspace permissions immediately.
- **FR-06 (UC-06): Workspace Metadata:** System shall store legal name, GSTIN, PAN, registered address, and state/district.
- **FR-07 (UC-07): Workspace Archival:** System shall soft-delete and archive inactive workspaces while preserving audit records.
- **FR-08 (UC-08): User Multi-Tenancy:** Single user identity shall belong to multiple workspaces with distinct role authorizations.

### Module 2: Khata & Customer Receivables (UC-09 to UC-16)
- **FR-09 (UC-09): Customer Registration:** Register customer accounts with name, phone, email, and billing address.
- **FR-10 (UC-10): Credit Limit Enforcement:** Prohibit sales invoices exceeding the defined customer credit limit.
- **FR-11 (UC-11): Credit Period Tracking:** Maintain credit periods in days (e.g., 30, 45, 60 days) per customer.
- **FR-12 (UC-12): Customer Ledger Balances:** Maintain real-time running balances updated by sales and collections.
- **FR-13 (UC-13): Payment Collection:** Record payments against customer balances via CASH, UPI, BANK_TRANSFER, or CHEQUE.
- **FR-14 (UC-14): Customer Ledger History:** Provide chronologically ordered, double-entry audit history of customer transactions.
- **FR-15 (UC-15): CSV Ledger Export:** Export customer ledgers with formula injection protection (OWASP guidelines).
- **FR-16 (UC-16): Customer Search & Filter:** Filter customers by outstanding balance, credit status, and name.

### Module 3: Vendor Payables & Procurement (UC-17 to UC-24)
- **FR-17 (UC-17): Supplier Registration:** Register vendor profiles with contact person, phone, email, and address.
- **FR-18 (UC-18): Payment Terms:** Store vendor payment terms (e.g., Net 15, Net 30 days).
- **FR-19 (UC-19): Supplier Payables Balance:** Automatically increment vendor liability upon procurement bill posting.
- **FR-20 (UC-20): Supplier Settlement:** Record settlements reducing vendor payable balance with payment channel tracking.
- **FR-21 (UC-21): Supplier Ledger History:** Immutable double-entry ledger of vendor procurement bills and cash outflows.
- **FR-22 (UC-22): Supplier CSV Export:** Downloadable CSV of supplier history with running liability balances.
- **FR-23 (UC-23): Supplier Archival:** Archive inactive suppliers while retaining historical purchase records.
- **FR-24 (UC-24): Payables Due Alert:** Highlight supplier bills due within 7 days.

### Module 4: Perpetual Inventory & WAC Valuation (UC-25 to UC-32)
- **FR-25 (UC-25): Product Catalog:** Manage SKU codes, product names, categories, and units of measure.
- **FR-26 (UC-26): Perpetual Stock Tracking:** Maintain real-time stock balances updated on every inward/outward movement.
- **FR-27 (UC-27): Weighted Average Cost (WAC):** Recalculate unit cost upon new purchases:
  $$\text{WAC}_{\text{new}} = \frac{(\text{Stock}_{\text{prev}} \times \text{Cost}_{\text{prev}}) + (\text{Qty}_{\text{new}} \times \text{Price}_{\text{new}})}{\text{Stock}_{\text{prev}} + \text{Qty}_{\text{new}}}$$
- **FR-28 (UC-28): Total Stock Valuation:** Compute inventory asset value as $\sum (\text{Qty}_i \times \text{WAC}_i)$.
- **FR-29 (UC-29): Reorder Level Alerts:** Surface warnings when stock drops below defined threshold.
- **FR-30 (UC-30): Manual Stock Adjustments:** Support stock physical audit counts, damages, and loss adjustments.
- **FR-31 (UC-31): Immutable Movement Ledger:** Record every inventory addition and deduction with audit reason.
- **FR-32 (UC-32): Inventory Out-of-Stock Prevention:** Reject invoices requesting stock exceeding available on-hand balance.

### Module 5: Sales Invoicing & Stock Integration (UC-33 to UC-40)
- **FR-33 (UC-33): Multi-Item Invoices:** Issue invoices with multiple line items, unit prices, discounts, and tax rates.
- **FR-34 (UC-34): Automatic Stock Decrement:** Decrement perpetual inventory stock immediately upon invoice issuance.
- **FR-35 (UC-35): Automatic Receivable Update:** Charge uncollected invoice totals to customer Khata balance.
- **FR-36 (UC-36): Invoice Status Workflow:** Transition invoices through DRAFT, ISSUED, PARTIALLY_PAID, PAID, OVERDUE, CANCELLED.
- **FR-37 (UC-37): Partial Payment Recording:** Support multiple sequential payment receipts against an invoice.
- **FR-38 (UC-38): Cash / Spot Sales:** Handle immediate point-of-sale cash transactions without creating customer debt.
- **FR-39 (UC-39): Invoice Cancellation:** Support cancellation with automatic inventory restocking and ledger reversal.
- **FR-40 (UC-40): Invoice Filtering:** Filter invoices by status, date range, and customer.

### Module 6: Purchases & Bill Settlements (UC-41 to UC-48)
- **FR-41 (UC-41): Procurement Bills:** Record vendor purchase orders with bill numbers and itemized costs.
- **FR-42 (UC-42): Automatic Stock Increment:** Increment inventory stock on hand immediately upon bill posting.
- **FR-43 (UC-43): Automatic Payables Update:** Add unpaid bill amount to supplier Khata account.
- **FR-44 (UC-44): Bill Status Workflow:** Transition bills through PENDING, RECEIVED, PARTIALLY_PAID, PAID, CANCELLED.
- **FR-45 (UC-45): Bill Payment Recording:** Record bank/cash settlements against specific purchase bills.
- **FR-46 (UC-46): Spot Purchases:** Support immediate cash purchases without creating supplier liabilities.
- **FR-47 (UC-47): Purchase Order Reference:** Link procurement bills to external PO numbers and delivery challans.
- **FR-48 (UC-48): Purchase History Audit:** Provide date-filtered purchase logs for tax reconciliation.

### Module 7: Cash Position & Operational Goals (UC-49 to UC-56)
- **FR-49 (UC-49): Direct Income Tracking:** Record non-invoice revenues (capital injections, interest, scrap sales).
- **FR-50 (UC-50): Direct Expense Tracking:** Record non-procurement expenses (salaries, electricity, rent, travel).
- **FR-51 (UC-51): Liquid Cash Breakdown:** Compute cash-in-hand and bank balances deterministically from cash transactions.
- **FR-52 (UC-52): Net Liquid Working Capital:** Real-time computation: $(\text{Cash} + \text{Receivables}) - \text{Payables}$.
- **FR-53 (UC-53): Operational Goal Definition:** Define milestone targets for Revenue, Profit, Cash Reserves, or Expense Reduction.
- **FR-54 (UC-54): Milestone Dates:** Set start and target milestone dates per goal.
- **FR-55 (UC-55): Automated Goal Recalculation:** Calculate goal progress percentage dynamically against live ledger totals.
- **FR-56 (UC-56): Goal Status:** Automatically classify goals as NOT_STARTED, IN_PROGRESS, ACHIEVED, or MISSED.

### Module 8: Deterministic Financial Intelligence (UC-57 to UC-64)
- **FR-57 (UC-57): Profit & Loss Statement:** Compute gross revenue, COGS (derived from sales line item WAC), gross profit, OPEX, EBITDA, and net profit before tax.
- **FR-58 (UC-58): Multi-Stream Cash Flow:** Reconcile Operating, Investing, and Financing cash movements with opening and closing cash.
- **FR-59 (UC-59): Solvency Ratios:** Compute Current Ratio ($\text{Current Assets} / \text{Current Liabilities}$) and Quick Ratio ($(\text{Cash} + \text{Receivables}) / \text{Current Liabilities}$).
- **FR-60 (UC-60): Solvency Health Classification:** Classify solvency as STRONG ($\ge 1.5$), ADEQUATE ($1.1 - 1.49$), STRESSED ($0.8 - 1.09$), or INSOLVENT ($< 0.8$).
- **FR-61 (UC-61): Receivables Ageing Buckets:** Partition outstanding customer dues into 0-30, 31-60, 61-90, and 90+ days.
- **FR-62 (UC-62): Payables Ageing Buckets:** Partition vendor liabilities into 0-30, 31-60, 61-90, and 90+ days.
- **FR-63 (UC-63): Break-Even & Safety Margin:** Calculate monthly break-even units and revenue, contribution margin ratio, and margin of safety %.
- **FR-64 (UC-64): 5-Pillar Health Score:** Compute composite 0-100 score across Liquidity, Profitability, Efficiency, Solvency, and Growth with strengths and vulnerability diagnoses.

### Module 9: Decision Laboratory & Versioned Models (UC-65 to UC-72)
- **FR-65 (UC-65): Model 1 (Equipment Purchase):** Evaluate capital equipment acquisition (the flagship ₹8L rotary oven) comparing bank loan vs. status quo vs. self-financing.
- **FR-66 (UC-66): Model 2 (New Product Line):** Evaluate product introduction with setup tooling, unit margins, and launch marketing.
- **FR-67 (UC-67): Model 3 (Supplier Switch):** Evaluate vendor migration comparing price discount against credit term shrinkage and minimum order constraints.
- **FR-68 (UC-68): Model 4 (Bulk Discount vs Storage):** Evaluate volume purchase savings against warehouse holding and capital tie-up costs.
- **FR-69 (UC-69): Model 5 (New Branch Location):** Evaluate physical branch expansion with rental security deposits, fit-out capex, and catchment revenue.
- **FR-70 (UC-70): Model 6 (Hiring Staff vs Commission):** Evaluate fixed salary personnel vs. variable commission sales incentives.
- **FR-71 (UC-71): Model 7 (Credit Term Extension):** Evaluate granting extended customer credit terms against bad debt risk and working capital drag.
- **FR-72 (UC-72): Model 8 (Price Elasticity & Discount):** Evaluate price changes against demand elasticity and contribution margin.

### Module 10: Monte Carlo & Sensitivity Simulation (UC-73 to UC-80)
- **FR-73 (UC-73): 1,000-Path Monte Carlo Simulation:** Execute 1,000 stochastic iterations using NumPy `PCG64` for reproducible pseudo-random numbers.
- **FR-74 (UC-74): Percentile Output Metrics:** Compute P10 (downside/pessimistic), P50 (median), and P90 (upside/optimistic) outcomes for NPV, IRR, and monthly cash flow.
- **FR-75 (UC-75): Downside Shortfall Probability:** Compute exact probability percentage of negative cash impact or debt covenant breach.
- **FR-76 (UC-76): Value-at-Risk (VaR 95%):** Compute the maximum estimated financial loss at the 95% confidence interval.
- **FR-77 (UC-77): Confidence Verdict Classification:** Categorize simulation outcomes into HIGH_CONFIDENCE_VIABLE, MODERATE_RISK_VIABLE, HIGH_RISK_CAUTION, or UNVIABLE.
- **FR-78 (UC-78): One-At-A-Time (OAT) Sensitivity:** Vary each key input variable by $\pm 20\%$ deterministically while holding all others constant.
- **FR-79 (UC-79): Elasticity Ratio Ranking:** Rank sensitivity variables by impact swing: $\text{Elasticity} = \frac{\% \Delta \text{Outcome}}{\% \Delta \text{Input}}$.
- **FR-80 (UC-80): Tornado Swings:** Return ordered swing limits for frontend horizontal Tornado chart visualization.

### Module 11: Agentic Gemini Copilot & Tool DAG (UC-81 to UC-90)
- **FR-81 (UC-81): Natural Language Inquiry:** Understand micro-entrepreneur conversational queries regarding investments, debts, and cash flow.
- **FR-82 (UC-82): Credential & Secret Firewall:** Sanitize all outbound AI context to strictly prevent credential or API key leakage.
- **FR-83 (UC-83): 16-Tool Registry:** Provide 16 strictly deterministic backend tools with validated Pydantic schemas.
- **FR-84 (UC-84): Zero-Hallucination Arithmetic:** Prohibit Gemini from performing financial calculations in prompt text; all computations must invoke deterministic tools.
- **FR-85 (UC-85): Multi-Step Investigation DAG:** Generate structured execution plans with sequential tool calls, step purposes, and dependency tracking.
- **FR-86 (UC-86): Tool Execution Auditing:** Record status (`PLANNED`, `EXECUTED`, `FAILED`, `SKIPPED`) and tool output summaries per step.
- **FR-87 (UC-87): Data Gap Identification:** Detect missing critical facts (e.g. loan interest rate, supplier lead time) rather than synthesizing estimates.
- **FR-88 (UC-88): Follow-Up Question Formulation:** Present specific clarification questions to the user when essential parameters are missing.
- **FR-89 (UC-89): Plain-Language Guidance Synthesis:** Generate actionable, contextual executive recommendations explaining the "why" behind the numbers.
- **FR-90 (UC-90): Autonomous Fallback Planning:** Maintain local deterministic investigation DAG planners for high-reliability offline execution.

### Module 12: Reporting, Governance & Audit Trails (UC-91 to UC-100)
- **FR-91 (UC-91): 2-Page Executive Decision Brief PDF:** Generate a publication-quality 2-page PDF with executive summary, 3-alternative ranking table, Monte Carlo distribution, and risk verdicts.
- **FR-92 (UC-92): Complete Business Dossier PDF:** Generate a multi-section PDF compiling business profile, P&L, balance sheet, solvency ratios, ageing buckets, and inventory valuation.
- **FR-93 (UC-93): ReportLab Flowable Typography:** Format PDFs with corporate headers, pagination, tables, and color-coded status badges.
- **FR-94 (UC-94): Customer CSV Ledger:** Export sanitized CSV ledgers for customers.
- **FR-95 (UC-95): Supplier CSV Ledger:** Export sanitized CSV ledgers for suppliers.
- **FR-96 (UC-96): OWASP Formula Injection Protection:** Strip leading `=`, `+`, `-`, `@`, `\t`, `\r` from exported CSV cells to prevent spreadsheet formula injection attacks.
- **FR-97 (UC-97): Decision Audit Persistence:** Persist all decision evaluations, alternative rankings, and constraints in PostgreSQL history.
- **FR-98 (UC-98): Historical Evaluation Retrieval:** Retrieve and inspect past decision briefs by ID.
- **FR-99 (UC-99): Immutable Stock Movement Logs:** Ensure stock movement audit entries cannot be modified or deleted.
- **FR-100 (UC-100): End-to-End Traceability:** Guarantee that every financial number in a report or decision brief is traceable to a specific transaction in the operational database.

---

## 4. Non-Functional Requirements

### 4.1 Reliability & Determinism
- 100% of arithmetic calculations shall be computed in Python with standard IEEE Decimal representation.
- Floating-point rounding errors are prohibited for currency balances; `Money` Value Object with `Decimal` arithmetic shall be used exclusively.
- Monte Carlo simulations shall support deterministic pseudo-random seeds (`PCG64`) for repeatable verification.

### 4.2 Performance
- API response times for transactional endpoints (invoices, payments, products) shall be under 150ms.
- Financial statement calculations (P&L, Cash Flow, Solvency) shall complete in under 250ms for ledgers with up to 10,000 entries.
- 1,000-iteration Monte Carlo simulations shall execute in under 300ms using vectorized NumPy arrays.
- PDF generation shall complete in under 1,500ms.

### 4.3 Security & Integrity
- All passwords shall be hashed using BCrypt.
- API authentication shall use signed JWT tokens (HMAC-SHA256) with role-based claim validation.
- Workspaces shall enforce strict multi-tenant boundary isolation; cross-workspace data leakage is strictly prohibited.
- CSV downloads shall enforce OWASP formula sanitization.

### 4.4 Usability & Aesthetics
- Frontend shall feature a liquid-glass design language with blurred backdrops, crisp typography, and responsive layouts.
- Business Constellation shall render an interactive 3D WebGL galaxy showing business nodes and operational health glow with graceful fallbacks.
- Zero empty screens: informative empty states and guided creation modals shall accompany every section.
