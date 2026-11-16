# Architecture Specification & System Design
## ArthLens: Business Operating System & Decision Intelligence Platform

**Architecture Standard:** C4 Model & IEEE 1471  
**Project:** ArthLens  
**Repository:** `C:\arthlens`  
**Core Architectural Thesis:**  
$$\text{ArthLens} = \text{Business Operating System} + \text{Financial Intelligence} + \text{Decision Intelligence} + \text{Agentic AI}$$  
**Version:** 2.0.0-RELEASE  
**Date:** November 2026  

> **Implementation status:** This is inherited design documentation. Treat feature and architecture statements below as design intent until checked against current source; no full product or release verification has been established. See [Engineering Handover](ENGINEERING_HANDOVER.md).

---

## 1. Executive Architectural Summary

ArthLens is an integrated software platform for micro-, small-, and medium-sized enterprises (MSMEs). Unlike fragmented accounting tools, generic chatbots, or static spreadsheet calculators, ArthLens unifies:
1. **The Operational Source of Truth (Business OS):** Captures everyday customer receivables, vendor payables, perpetual stock adjustments with Weighted Average Cost (WAC) valuation, and sales invoicing.
2. **Deterministic Financial Intelligence:** Automatically derives P&L, multi-stream Cash Flow, 90-day Ageing, Solvency ratios, Break-Even analysis, and a 5-pillar composite Health Score.
3. **Decision Intelligence & Simulation Engine:** Evaluates consequential capital and operating decisions across 8 versioned models, executes 1,000-iteration Monte Carlo PCG64 risk simulations, and computes One-At-A-Time (OAT) Tornado sensitivity swings.
4. **Agentic Gemini AI Copilot:** Employs Gemini 2.5 to understand owner inquiries, formulate multi-step investigation DAG plans, call 16 deterministic application tools, surface data gaps, and synthesize actionable guidance without performing synthetic math.
5. **Governance & Reporting:** Generates 2-page executive decision briefs and complete business dossiers in ReportLab PDF format alongside OWASP formula-sanitized CSV exports.

---

## 2. C4 Architecture Model

### Level 1: System Context Diagram

```mermaid
flowchart TD
    User["Micro-Entrepreneur / Business Owner"]
    Manager["Store Manager / Accountant"]
    Bank["Banking / Lending Partner"]

    subgraph ArthLens["ArthLens Platform"]
        CoreSys["Business OS & Decision Intelligence Platform"]
    end

    Gemini["Google Gemini 2.5 LLM"]
    PDFEng["ReportLab PDF Generator"]
    Postgres[("PostgreSQL 16 Database")]

    User -->|"1. Views 3D Constellation & Evaluates Decisions"| CoreSys
    Manager -->|"2. Records Khata, Invoices & Purchases"| CoreSys
    CoreSys -->|"3. Natural Language Query Planning"| Gemini
    CoreSys -->|"4. Compiles Executive Decision Briefs"| PDFEng
    CoreSys -->|"5. Double-Entry Immutable Persistence"| Postgres
    PDFEng -->|"6. Downloadable 2-Page Briefs & Dossiers"| Bank
```

### Level 2: Container Diagram

```mermaid
flowchart TD
    subgraph ClientTier["Client Tier (Browser)"]
        NextApp["Next.js 14 Motion-Led Web App"]
        Constellation["Three.js 3D Business Constellation"]
        Hub["Liquid-Glass Operating Hub & Decision Lab"]
    end

    subgraph APITier["Application Server Tier (FastAPI)"]
        Gateway["FastAPI API Gateway (Port 8000)"]
        AuthMid["JWT Auth & Multi-Tenant Isolation Middleware"]
        BOSService["Business Service (Orchestration)"]
        FinEngine["Financial Intelligence Engine"]
        DecEngine["Decision Intelligence Engine"]
        SimEngine["Monte Carlo & Sensitivity Engine"]
        AgentEngine["Agentic Gemini Copilot & Tool Registry"]
        RepEngine["ReportLab PDF & CSV Generator"]
    end

    subgraph DataTier["Data Tier"]
        DB[("PostgreSQL 16 (Port 5433:5432)")]
    end

    NextApp --> Constellation
    NextApp --> Hub
    Hub -->|"REST / JSON"| Gateway
    Gateway --> AuthMid
    AuthMid --> BOSService
    AuthMid --> FinEngine
    AuthMid --> DecEngine
    AuthMid --> SimEngine
    AuthMid --> AgentEngine
    AuthMid --> RepEngine

    BOSService --> DB
    FinEngine --> DB
    DecEngine --> DB
    SimEngine --> DecEngine
    AgentEngine --> BOSService
    AgentEngine --> FinEngine
    AgentEngine --> DecEngine
    RepEngine --> DB
```

### Level 3: Component Diagram (Backend Core)

```mermaid
flowchart LR
    subgraph Presentation["API Layer (backend.arthlens.api)"]
        BusRouter["business.py Router"]
        Schemas["Pydantic v2 Request/Response Schemas"]
    end

    subgraph Domain["Domain Layer (backend.arthlens.domain)"]
        VO["Value Objects: Money, Percentage, DateRange"]
        Entities["Entities: Business, Customer, Supplier, Product, Invoice, Purchase, Goal"]
    end

    subgraph Service["Application Services (backend.arthlens.services)"]
        BusServ["BusinessService"]
    end

    subgraph Financial["Financial Intelligence (backend.arthlens.finance)"]
        FinIntell["FinancialIntelligenceEngine"]
    end

    subgraph Decision["Decision Intelligence (backend.arthlens.decision)"]
        DecModels["8 Versioned Decision Models (v1.0.0)"]
        DecEngine["DecisionIntelligenceEngine"]
        SimEng["MonteCarloSimulator & SensitivityAnalyzer"]
    end

    subgraph AgenticAI["Agentic AI Layer (backend.arthlens.agent)"]
        ToolReg["BusinessToolRegistry (16 Registered Tools)"]
        Agent["BusinessAgent (Gemini 2.5 + Fallback DAG)"]
    end

    subgraph Infrastructure["Infrastructure Layer (backend.arthlens.infra)"]
        Repos["11 Postgres Repositories"]
        ORM["16 SQLAlchemy Models"]
    end

    BusRouter --> Schemas
    BusRouter --> BusServ
    BusRouter --> FinIntell
    BusRouter --> DecEngine
    BusRouter --> Agent

    BusServ --> Repos
    FinIntell --> Repos
    DecEngine --> FinIntell
    DecEngine --> Repos
    Agent --> ToolReg
    ToolReg --> BusServ
    ToolReg --> FinIntell
    ToolReg --> DecEngine

    Repos --> ORM
```

---

## 3. Domain Model & Class Architecture

### Value Objects & Immutability
All monetary values are encapsulated within the immutable `Money` Value Object:
- Backed by Python standard library `Decimal` with exact 2-decimal precision.
- Implements arithmetic operator overloading (`+`, `-`, `*`, `/`).
- Format method: `format_inr()` producing Indian numbering formatting (e.g. `₹8,00,000.00`).
- Floating-point arithmetic on currency is strictly forbidden.

```mermaid
classDiagram
    class Money {
        +Decimal amount
        +str currency
        +add(Money) Money
        +sub(Money) Money
        +mul(Decimal) Money
        +div(Decimal) Money
        +format_inr() str
        +to_float() float
    }

    class BusinessWorkspace {
        +UUID id
        +str name
        +str industry
        +str address
        +bool is_active
        +datetime created_at
    }

    class Customer {
        +UUID id
        +UUID business_id
        +str name
        +str phone
        +Money credit_limit
        +Money current_balance
    }

    class Supplier {
        +UUID id
        +UUID business_id
        +str name
        +str phone
        +int payment_terms_days
        +Money current_balance
    }

    class Product {
        +UUID id
        +UUID business_id
        +str sku
        +str name
        +str unit
        +Money purchase_price
        +Money selling_price
    }

    class InventoryBalance {
        +UUID id
        +UUID business_id
        +UUID product_id
        +Decimal quantity_on_hand
        +Money unit_cost
        +Money total_valuation
        +apply_addition(qty, unit_cost)
        +apply_deduction(qty)
    }

    class SalesInvoice {
        +UUID id
        +UUID business_id
        +UUID customer_id
        +str invoice_number
        +date invoice_date
        +date due_date
        +Money subtotal
        +Money tax_amount
        +Money total_amount
        +Money paid_amount
        +InvoiceStatus status
        +outstanding_balance Money
        +record_payment(Money)
    }

    class Purchase {
        +UUID id
        +UUID business_id
        +UUID supplier_id
        +str bill_number
        +date purchase_date
        +Money total_amount
        +Money paid_amount
        +PurchaseStatus status
        +outstanding_balance Money
        +record_payment(Money)
    }

    BusinessWorkspace "1" *-- "many" Customer
    BusinessWorkspace "1" *-- "many" Supplier
    BusinessWorkspace "1" *-- "many" Product
    Product "1" *-- "1" InventoryBalance
    BusinessWorkspace "1" *-- "many" SalesInvoice
    BusinessWorkspace "1" *-- "many" Purchase
    Customer "1" *-- "many" SalesInvoice
    Supplier "1" *-- "many" Purchase
```

---

## 4. Sequence Diagrams of Key Architectural Workflows

### 4.1 Sales Invoicing with Stock Decrement & Khata Receivable

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Business Owner
    participant Web as Next.js Invoicing UI
    participant API as FastAPI Router
    participant Service as BusinessService
    participant CustRepo as CustomerRepository
    participant InvRepo as InventoryRepository
    participant InvcRepo as InvoiceRepository

    Owner->>Web: Create Sales Invoice (200 loaves @ ₹60)
    Web->>API: POST /businesses/{id}/invoices
    API->>Service: create_sales_invoice(...)
    Service->>CustRepo: Verify Customer Credit Limit
    CustRepo-->>Service: Credit Limit OK (₹12,600 <= ₹1,00,000)
    Service->>InvRepo: Check On-Hand Stock (Product BAKE-BREAD-01)
    InvRepo-->>Service: On-Hand Stock = 500 units
    Service->>InvRepo: Deduct 200 units -> New Stock = 300 units
    Service->>InvRepo: Record Immutable InventoryMovement (Type: SALE)
    Service->>InvcRepo: Save SalesInvoice (Total = ₹12,600, Outstanding = ₹12,600)
    Service->>CustRepo: Increment Customer Current Balance (+₹12,600)
    InvcRepo-->>API: Invoice Entity
    API-->>Web: HTTP 201 Created (Updated Balances)
    Web-->>Owner: Displays Invoice Badge & Decremented Stock
```

### 4.2 Flagship ₹8 Lakh Rotary Oven Decision Evaluation & Simulation

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Business Owner
    participant UI as Decision Lab UI
    participant API as Decisions Router
    participant DecEng as DecisionIntelligenceEngine
    participant FinEng as FinancialIntelligenceEngine
    participant MC as MonteCarloSimulator (PCG64)
    participant OAT as SensitivityAnalyzer
    participant RepGen as BusinessReportGenerator

    Owner->>UI: Selects "Machine Purchase" & Submits ₹8L Oven Parameters
    UI->>API: POST /businesses/{id}/decisions/evaluate
    API->>DecEng: evaluate_decision("MACHINE_OR_EQUIPMENT_PURCHASE", inputs)
    DecEng->>FinEng: Fetch Live Operating Cash & Revenue Baseline
    FinEng-->>DecEng: Cash = ₹3,56,300, EBITDA, DSCR
    DecEng->>DecEng: Evaluate 3 Alternatives (Loan 36M, Loan 60M, Self-Financed)
    DecEng->>DecEng: Compute NPV, Payback (14.2 Mo), DSCR (2.88x), Rank 1
    DecEng-->>API: Evaluation Result (Ranked Alternatives, Graph)
    API-->>UI: Displays 3-Alternative Ranking Table

    UI->>API: POST /businesses/{id}/decisions/simulate-risk (1,000 runs)
    API->>MC: run_simulation(model, inputs, iterations=1000)
    MC-->>API: P10, P50, P90 Percentiles & VaR 95%
    API-->>UI: Renders Risk Distribution Chart

    UI->>API: POST /businesses/{id}/decisions/sensitivity (OAT ±20%)
    API->>OAT: run_sensitivity(model, inputs, target="net_monthly_cash_flow")
    OAT-->>API: Tornado Swings & Elasticity Ranking
    API-->>UI: Renders Tornado Horizontal Swings

    Owner->>UI: Clicks "Download Decision Brief (PDF)"
    UI->>API: GET /businesses/{id}/reports/decisions/{eval_id}/brief.pdf
    API->>RepGen: generate_decision_brief_pdf(business, evaluation)
    RepGen-->>API: Binary PDF Stream (%PDF-1.4, 2 Pages)
    API-->>UI: PDF Download Initiated
```

### 4.3 Agentic Copilot Investigation DAG Execution

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Business Owner
    participant Chat as Copilot Chat UI
    participant API as Agent Router
    participant Agent as BusinessAgent
    participant LLM as Google Gemini 2.5
    participant Tools as BusinessToolRegistry
    participant Service as Business Operating System

    Owner->>Chat: "Should we buy the 8 lakh rotary oven for the bakery?"
    Chat->>API: POST /businesses/{id}/agent/investigate
    API->>Agent: investigate(business_id, query)
    Agent->>Agent: Sanitize context via CredentialFirewall
    Agent->>LLM: Formulate Multi-Step Investigation DAG
    LLM-->>Agent: DAG Plan: [Step 1: get_cash_position, Step 2: evaluate_decision_model, Step 3: simulate_risk]
    
    loop For each step in DAG
        Agent->>Tools: Execute registered deterministic tool
        Tools->>Service: Query actual database records
        Service-->>Tools: Deterministic mathematical result
        Tools-->>Agent: Validated Pydantic output
    end

    Agent->>LLM: Synthesize explanation using tool evidence only
    LLM-->>Agent: Recommendation: "PROCEED with loan financing; DSCR 2.88x is robust."
    Agent-->>API: Investigation Response (Plan, Evidence, Gaps, Synthesis)
    API-->>Chat: Renders Synthesis, Action Checklist & DAG Nodes
```

---

## 5. Security & Multi-Tenancy Architecture

### 5.1 Credential & Secret Firewall
To ensure strict security and prevent prompt injection or credential exfiltration:
- The `CredentialFirewall` sanitizes all strings before forwarding to external LLM providers.
- API keys, database credentials, JWT secrets, and environment tokens are stripped from prompts.
- Outbound responses are filtered for credential leaks.

### 5.2 Multi-Tenant Workspace Boundary Isolation
- Every database entity (`CustomerModel`, `SalesInvoiceModel`, `ProductModel`, etc.) is tagged with a mandatory `business_id` foreign key.
- Repositories enforce `WHERE business_id = :business_id` on all read, update, and delete queries.
- `BusinessService.verify_access(business_id, user_id)` verifies that the caller has an active `BusinessMembership` with appropriate role permissions before dispatching operations.

### 5.3 OWASP Formula Injection Sanitization
All CSV ledger downloads implement the OWASP standard for formula injection prevention:
- Cells beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` are prefixed with an apostrophe `'`.
- Prohibits malicious CSV payload execution in Microsoft Excel or Google Sheets.

---

## 6. Deployment Architecture

```mermaid
flowchart TD
    subgraph Host["Host Environment (Windows Server / Linux)"]
        Docker["Docker Compose"]
        subgraph Containers["Containers"]
            PostgreSQL["PostgreSQL 16 (arthlens-postgres:5432 / Host:5433)"]
        end
        subgraph HostProcesses["Host Services"]
            FastAPI["FastAPI Uvicorn Worker (Port 8000)"]
            NextJS["Next.js 14 Production Server (Port 3000)"]
        end
    end

    Client["Web Browser Client"] -->|"HTTPS / Port 3000"| NextJS
    NextJS -->|"Internal HTTP / Port 8000"| FastAPI
    FastAPI -->|"TCP / Port 5433"| PostgreSQL
```

- **Database:** PostgreSQL containerized via Docker on port 5433 host mapping.
- **Backend:** FastAPI running under Uvicorn ASGI with auto-worker scaling.
- **Frontend:** Next.js 14 running production build with standalone SSR support.
- **Auditability:** Zero external SaaS dependencies for core financials or PDF generation; 100% self-contained on premise.
