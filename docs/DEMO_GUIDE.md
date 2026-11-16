# ArthLens Flagship Demonstration Guide

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform  
**Target Scenario:** Multi-Enterprise Micro-Entrepreneur Demonstration Journey  
**Estimated Demo Time:** 8–10 Minutes

> **Execution status:** This is a proposed demo script. Its complete journey has not been reproduced against a clean database during the current review. See [Engineering Handover](ENGINEERING_HANDOVER.md).

---

## 1. Demonstration Narrative Overview

In this demonstration, you embody **Aarav Sharma**, a successful entrepreneur operating two enterprises in Uttar Pradesh:
1. **Varanasi Silk Emporium** (Textiles & Handloom, high revenue, credit customer ledger).
2. **Kanpur Leather Goods** (Manufacturing & Export, high inventory volume, supplier debt).

You will demonstrate the 4 pillars of ArthLens:
- **Pillar 1: Multi-Business Operating System** (Constellation view, Customer Khata, Product Inventory, Sales Invoicing).
- **Pillar 2: Financial Intelligence** (Deterministic P&L, Working Capital, Cash Runway, Composite Health Score).
- **Pillar 3: Decision Intelligence** (Weaving Loom Expansion, 3 Alternatives, NPV/Payback, Monte Carlo Risk).
- **Pillar 4: Agentic AI Co-pilot** (Google Gemini autonomous investigation with strict tenant security and fact provenance).

---

## 2. Step-by-Step Walkthrough

### Step 1: Login & Constellation Galaxy
1. Open `http://localhost:3000/login`.
2. Enter demo credentials:
   - **Email**: `entrepreneur@arthlens.org`
   - **Password**: `Password123!`
3. Click **Sign In**.
4. **Talking Point**: Point out the **liquid-glass Business Constellation** on the home dashboard. Highlight that both businesses are actively tracked with live cash balances, burn rates, runway metrics, and health scores (82/100 and 74/100).

### Step 2: Operational Workspaces & Khata
1. Click on **Varanasi Silk Emporium**.
2. Navigate to **Khata** (`/workspaces/[id]/khata`).
3. Show the customer directory:
   - Notice **Kashi Handloom Co.** has an outstanding balance of ₹85,000 against a ₹1,50,000 credit limit.
4. Click **"Record Payment"** and log ₹25,000 received via UPI.
5. **Talking Point**: Notice the real-time balance immediately drops to ₹60,000 and the cash ledger updates with zero page reloads.

### Step 3: Product Inventory & Invoicing
1. Navigate to **Sales** (`/workspaces/[id]/sales`).
2. Click **"+ New Invoice"**.
3. Select customer **Kashi Handloom Co.**, select product **Banarasi Silk Saree** (Qty: 5 @ ₹12,000 each).
4. Click **"Issue Invoice"**.
5. **Talking Point**: Show that:
   - Total ₹60,000 + GST is calculated deterministically.
   - Warehouse stock is automatically decremented by 5 units.
   - Customer Khata balance increments atomically in a single database transaction.

### Step 4: Financial Intelligence Analytics
1. Navigate to **Analytics** (`/workspaces/[id]/analytics`).
2. Point out:
   - **Profit & Loss**: Gross Margin (64.2%), EBITDA, Net Margin (28.4%).
   - **Working Capital**: Debtor collection period (38 days) vs Creditor payment period (22 days).
   - **Cash Runway**: 14.2 months based on current average net monthly cash burn.
   - **Composite Health Score**: 84/100 (Graded: Low Operational Risk).
3. **Talking Point**: Emphasize that every single metric is computed by deterministic Python math from actual ledger entries, not estimated by an LLM.

### Step 5: Decision Intelligence & Risk Simulation
1. Navigate to **Decisions** (`/workspaces/[id]/decisions`).
2. Select decision model: **"Automatic Weaving Loom Acquisition"**.
3. Inspect the 3 competing alternatives:
   - **Alternative 1 (Cash Purchase)**: ₹4,50,000 upfront; zero interest; 18-month payback; NPV ₹2,10,000.
   - **Alternative 2 (3-Year MSME Term Loan)**: ₹50,000 down payment; 9.5% interest; ₹13,800/mo EMI; NPV ₹1,85,000.
   - **Alternative 3 (Operational Lease)**: ₹16,000/mo lease fee; zero down payment; NPV ₹1,40,000.
4. Click **"Run Monte Carlo Simulation"**.
5. **Talking Point**: 1,000 pseudo-random iterations simulate raw material price shocks and demand volatility. Alternative 2 emerges as the recommended choice because Alternative 1 violates the ₹2,00,000 minimum cash buffer constraint during month 3.

### Step 6: Agentic AI Co-pilot Investigation
1. Navigate to **Copilot** (`/workspaces/[id]/agent`).
2. Enter prompt: *"Can we afford to hire 2 master weavers next month at ₹25,000 salary each?"*
3. Watch the autonomous investigation:
   - Tool 1: Queries cash balance (₹4,25,000).
   - Tool 2: Calculates monthly fixed payroll increase (+₹50,000/mo).
   - Tool 3: Simulates revised burn rate and runway (drops from 14.2 to 11.8 months).
4. Inspect the synthesized reply with provenance badges (`OBSERVED`, `CALCULATED`).
5. **Talking Point**: The AI explicitly confirms affordability, notes that runway remains comfortably above the 6-month threshold, and warns about seasonal raw silk price surges in October.

---

## 3. Demo Closing Statement

*"ArthLens bridges the critical gap between daily business operations and consequential decision-making for Indian entrepreneurs. By uniting an operational source of truth with deterministic financial intelligence and governed agentic AI, ArthLens transforms small business operators into confident, evidence-backed decision makers."*
