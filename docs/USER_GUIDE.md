# ArthLens Operator & User Guide

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform  
**Target Audience:** Micro-Entrepreneurs, Multi-Enterprise Owners, Financial Managers, Business Operators

---

## 1. Getting Started & Account Registration

1. **Accessing ArthLens**: Open `http://localhost:3000` in your browser.
2. **Account Creation**: Navigate to **Register**, supply your name, email address, and a secure password (minimum 8 characters).
3. **Authentication**: Sign in using your registered credentials. Your session is securely maintained via encrypted HTTP-only session cookies.

---

## 2. Navigating the Business Constellation

The home dashboard features the **Business Constellation** view—a liquid-glass interactive map of all your enterprises:
- **Workspace Cards**: Displays real-time cash balance, monthly burn rate, runway months, health score (0-100), and operational status.
- **Enterprise Creation**: Click **"+ New Workspace"** to launch a new business by specifying its name, legal entity name, industry, and address.
- **Multi-Enterprise Switching**: Click any workspace card to transition instantly into that enterprise's dedicated operational dashboard.

---

## 3. Daily Operations & Khata Management

Within any workspace (`/workspaces/[id]`):

### 3.1 Khata (Customers & Suppliers)
- **Customer Directory**: Add customers, set credit limits, view current balances, and inspect complete ledger transaction histories.
- **Supplier Directory**: Register suppliers, set credit periods, view payable dues, and log supplier purchase invoices.
- **Dues Collection & Settlement**: Click **"Record Payment"** to log incoming customer receipts or outgoing vendor disbursements with automatic double-entry ledger adjustment.

### 3.2 Inventory & Stock Management
- **Product Catalog**: Add products with SKU, unit price, cost price, GST tax rates, and reorder levels.
- **Stock Movement Log**: Track automatic stock decrements upon invoice fulfillment and stock increments upon purchase delivery.
- **Reorder Alerts**: Products falling below minimum inventory thresholds trigger visual yellow/red replenishment warnings.

### 3.3 Invoicing & Purchases
- **Sales Invoices**: Generate professional, GST-compliant sales invoices. Select customers, add multi-item line items, and issue invoices. The system automatically updates customer khata and decrements warehouse stock.
- **Purchase Orders**: Order goods from suppliers, record delivery receipts, and update accounts payable.

---

## 4. Financial Intelligence Engine

Access the **Analytics** view (`/workspaces/[id]/analytics`) to view real-time, deterministic financial statements:
- **Profit & Loss**: Inspect gross revenue, COGS, gross margin, operating expenses, and net profit.
- **Cash Flow**: Track operating, investing, and financing cash movements.
- **Working Capital**: Evaluate debtor collection days, creditor payment days, and cash conversion cycles.
- **Ageing Analysis**: Review accounts receivable and accounts payable grouped into 0-30, 31-60, 61-90, and 90+ day categories.
- **Break-Even Calculator**: Discover the exact sales volume and revenue required to cover fixed operational overheads.

---

## 5. Decision Intelligence Engine & Scenario Simulation

Access the **Decisions** view (`/workspaces/[id]/decisions`) to model consequential choices:
- **Evaluating Choices**: Select a decision template (e.g., Equipment Financing, New Storefront Expansion, Supplier Bulk Purchase, or Team Hiring).
- **Hard Constraints**: Specify operational boundaries (e.g., minimum cash reserve of ₹2,00,000; maximum debt service ratio of 1.5).
- **Alternative Comparison**: Generate 3-4 mutually exclusive options (e.g., Option A: Outright Cash Purchase, Option B: 3-Year Commercial Loan, Option C: Equipment Lease).
- **Monte Carlo Risk Simulation**: Click **"Run Risk Simulation"** to execute 1,000 deterministic trial iterations assessing outcome probability distributions and default risks.

---

## 6. Collaborating with the Agentic AI Co-pilot

Access the **Copilot** view (`/workspaces/[id]/agent`):
- **Conversational Investigation**: Ask questions in plain language: *"What is my runway if raw material prices rise by 15%?"* or *"Which customers have overdue payments exceeding 60 days?"*
- **Explainable Evidence**: The AI plans and executes structured tools against your business records, presenting findings with exact provenance tags (`OBSERVED`, `CALCULATED`, `MODELLED`).
- **Missing Facts Prompting**: If a question requires unavailable information (e.g. prospective lease costs), the AI prompts you explicitly rather than guessing numbers.
