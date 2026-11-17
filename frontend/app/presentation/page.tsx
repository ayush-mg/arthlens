"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  ShieldCheck,
  Cpu,
  Layers,
  Database,
  GitBranch,
  Terminal,
  Activity,
  ArrowRight,
  ArrowLeft,
  Maximize2,
  Minimize2,
  FileText,
  Boxes,
  CheckCircle2,
  AlertTriangle,
  Play,
  Pause,
  Key,
  Users,
  Compass,
  Lock,
  GitMerge,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  BarChart3,
  Scale,
  RefreshCw,
  Hash
} from "lucide-react";

interface SlideData {
  id: number;
  category: string;
  title: string;
  subtitle: string;
  layout: "title" | "split" | "quad" | "tri" | "dense";
  badge?: string;
  cards: {
    title: string;
    badge?: string;
    tone?: "crimson" | "matcha" | "gold" | "ink";
    items: { label: string; desc: string }[];
  }[];
  equation?: string;
  footerNote?: string;
}

const SLIDES: SlideData[] = [
  // SLIDE 01
  {
    id: 1,
    category: "Course Project Submission // IIIT Allahabad",
    title: "ARTH LENS: Sovereign Financial Topology",
    subtitle: "Deterministic Integer-Paisa Khata, Perpetual FIFO Inventory & Staged AI Decision Platform",
    layout: "title",
    badge: "OOM CAPSTONE 2026",
    cards: [
      {
        title: "AYUSH MISHRA",
        badge: "STUDENT CREDENTIALS // ROLL NO: IIT2025108",
        tone: "crimson",
        items: [
          { label: "Course Focus", desc: "Object Oriented Methodologies (OOM) Core Curriculum" },
          { label: "Core Ownership", desc: "Clean Architecture layer boundaries, FastAPI dependency injection container, and multi-tenant isolation." },
          { label: "Domain Design", desc: "Aggregate roots (Invoice, Payment), repository port abstractions, and domain event dispatchers." },
          { label: "Key Invariant", desc: "Strict dependency inversion with zero external database ORM leakage in domain core." }
        ]
      },
      {
        title: "ABHAY PRATAP SINGH",
        badge: "STUDENT CREDENTIALS // ROLL NO: IIT2025109",
        tone: "matcha",
        items: [
          { label: "Course Focus", desc: "Object Oriented Methodologies (OOM) Core Curriculum" },
          { label: "Core Ownership", desc: "Double-entry journal engine, perpetual FIFO lot queue allocation algorithms, and algebraic reconciliation." },
          { label: "Domain Design", desc: "Money(paise: int) immutable value object, DuPont financial decomposition, and scenario simulator." },
          { label: "Key Invariant", desc: "Exact algebraic balance assertion (Sum Debits == Sum Credits) enforced on every voucher write." }
        ]
      },
      {
        title: "MAYANK PURI",
        badge: "STUDENT CREDENTIALS // ROLL NO: IIT2025104",
        tone: "gold",
        items: [
          { label: "Course Focus", desc: "Object Oriented Methodologies (OOM) Core Curriculum" },
          { label: "Core Ownership", desc: "Next.js visual topology, responsive design tokens, and lifecycle state machine flows." },
          { label: "Domain Design", desc: "Staged AI governance approval queues, dual-control confirmation gates, and Playwright E2E suites." },
          { label: "Key Invariant", desc: "Human-in-the-loop requirement: Zero unapproved mutations permitted across ledger records." }
        ]
      }
    ],
    footerNote: "Course Project for Object Oriented Methodologies | Indian Institute of Information Technology, Allahabad"
  },

  // SLIDE 02
  {
    id: 2,
    category: "Problem Statement & Industry Context",
    title: "The MSME Problem: Operational Chaos & Mathematical Drift",
    subtitle: "Why standard accounting software and generic ERPs cause catastrophic financial and architectural drift in manufacturing MSMEs.",
    layout: "quad",
    cards: [
      {
        title: "Floating-Point Rounding Corruption",
        badge: "CRITICAL FAILURE // DATA DRIFT",
        tone: "crimson",
        items: [
          { label: "Root Cause", desc: "Generic ERPs store money as standard IEEE 754 floating-point numbers (FLOAT/DOUBLE), creating binary fractional inaccuracies." },
          { label: "Accumulation Risk", desc: "Binary fractional rounding causes silent balance drift across thousands of high-velocity commercial journal entries." },
          { label: "Audit Failure", desc: "Trial balances fail to close to exact zero, triggering manual accounting reconciliations and tax filing penalties." },
          { label: "Architectural Aim", desc: "Enforce integer-paise arithmetic invariants at the domain compiler level to guarantee zero mathematical drift." }
        ]
      },
      {
        title: "Informal Credit Default Spiral",
        badge: "COMMERCIAL RISK // WORKING CAPITAL",
        tone: "gold",
        items: [
          { label: "Liquidity Crisis", desc: "Indian MSMEs face an average of ₹35L+ trapped in overdue receivables across unorganized distribution channels." },
          { label: "Ledger Silos", desc: "Commercial invoices are disconnected from cash receipts, masking overdue aging buckets and bad-debt velocity." },
          { label: "Cashflow Deception", desc: "Businesses appear profitable on paper while crashing due to operational liquidity starvation." },
          { label: "Architectural Aim", desc: "Atomic Khata synchronization linking invoices directly to settlement ledgers with real-time aging tracking." }
        ]
      },
      {
        title: "Inventory Blending Bias (Average Costing Lies)",
        badge: "SUPPLY CHAIN FLAW // MARGIN BLINDNESS",
        tone: "crimson",
        items: [
          { label: "Costing Distortion", desc: "Weighted-average inventory methods blend historical cheap stock with newly inflated shipments, distorting true unit cost." },
          { label: "Margin Erosion", desc: "Operators price finished goods against artificially low average costs, unknowingly selling products at a severe cash loss." },
          { label: "Batch Obscurity", desc: "Zero traceability for lot-specific batch expiration, supplier defect clusters, or shipment lead-time reliability." },
          { label: "Architectural Aim", desc: "Perpetual First-In, First-Out (FIFO) queue lot engine tracking exact batch acquisition costs down to individual sales." }
        ]
      },
      {
        title: "Rogue Autonomous AI Mutations",
        badge: "AI SAFETY HAZARD // GOVERNANCE DEFICIT",
        tone: "gold",
        items: [
          { label: "Hallucination Hazard", desc: "Modern LLM copilots often execute direct SQL updates or automated disbursements without human oversight." },
          { label: "Irreversible Loss", desc: "A single hallucinated invoice modification or erroneous payment write permanently pollutes immutable audit trails." },
          { label: "Lack of Governance", desc: "Absence of formal state machine gates between AI analytical reasoning and production database commitments." },
          { label: "Architectural Aim", desc: "Constrain AI agents to read-only tool DAGs with mandatory multi-party confirmation gates for all proposed mutations." }
        ]
      }
    ]
  },

  // SLIDE 03
  {
    id: 3,
    category: "End-to-End System Blueprint",
    title: "Platform Architecture: The 7-Step Sovereign Pipeline",
    subtitle: "Governing Balance Sheet Invariant: Assets(t) == Liabilities(t) + Equity(t) maintained through deterministic execution gates.",
    layout: "tri",
    equation: "CORE SYSTEM INVARIANT:  ∀ t ∈ Time : Assets(t) ≡ Liabilities(t) + Equity(t)   |   ΔDebits ≡ ΔCredits (Paisa-Exact)",
    cards: [
      {
        title: "Stage I: Ingestion & Normalization",
        badge: "PIPELINE STAGE I // BOUNDARY GATE",
        tone: "crimson",
        items: [
          { label: "Step 1: Event Ingestion", desc: "Sales invoices, purchase orders, inward bills, and payments enter via validated REST schemas." },
          { label: "Step 2: Integer Normalization", desc: "All financial inputs are converted to integer paisa (INR × 100). Floating points are rejected at the gateway boundary." },
          { label: "Data Contract", desc: "Strict Pydantic payload models enforce schema compliance, preventing null fields or negative quantities." },
          { label: "Tenant Isolation", desc: "Multi-tenant context injected automatically via cryptographically verified tenant JWT claims." }
        ]
      },
      {
        title: "Stage II: Atomic Core Computation",
        badge: "PIPELINE STAGE II // DETERMINISTIC ENGINE",
        tone: "matcha",
        items: [
          { label: "Step 3: Unit of Work", desc: "All related table mutations wrap inside an ACID transactional boundary with automated rollback on failure." },
          { label: "Step 4: FIFO Lot Engine", desc: "Purchases create discrete lots; sales consume oldest available lots, computing exact real-time COGS." },
          { label: "Step 5: Balanced Ledger Posting", desc: "Generates dual-entry journal vouchers ensuring zero imbalance between debits and credits." },
          { label: "Mathematical Proof", desc: "Sum of debits minus sum of credits strictly equals 0 paise before database commit is authorized." }
        ]
      },
      {
        title: "Stage III: Intelligence & Governance",
        badge: "PIPELINE STAGE III // COGNITION & AUDIT",
        tone: "gold",
        items: [
          { label: "Step 6: Intelligence Synthesis", desc: "Updates real-time financial ratios: DuPont decomposition, 90-day cashflow runway, and working capital cycles." },
          { label: "Step 7: Governed AI Action Gate", desc: "AI Copilot analyzes ledger data via read-only DAG tools. Mutations are queued as structured proposals." },
          { label: "Two-Person Confirmation", desc: "Operators review proposed actions (e.g., supplier restock) and authorize execution with digital signatures." },
          { label: "Audit Logging", desc: "Every mutation creates an immutable SHA-256 event log with operator signature and client IP telemetry." }
        ]
      }
    ]
  },

  // SLIDE 04
  {
    id: 4,
    category: "Functional Domain Decomposition",
    title: "Domain Modularity: The 18 Workspace Chapters",
    subtitle: "A comprehensive, multi-tenant enterprise suite structured across four cohesive operational quadrants.",
    layout: "quad",
    cards: [
      {
        title: "Commerce & Inventory Core (Ch 01 - 05)",
        badge: "QUADRANT I // SUPPLY CHAIN & COMMERCE",
        tone: "crimson",
        items: [
          { label: "01. Sales & GST Invoicing", desc: "Compliant B2B/B2C invoices, HSN code lookups, reverse charges, and auto-Khata linking." },
          { label: "02. Purchase & Inward Bills", desc: "Supplier inward shipments, vendor bill reconciliation, and purchase order tracking." },
          { label: "03. Perpetual FIFO Inventory", desc: "Real-time lot allocation, multi-warehouse stock tracking, and reorder velocity alerts." },
          { label: "04. Customer Khata Directory", desc: "Party credit limits, aging buckets (0-30, 31-60, 90+ days), and collection history." },
          { label: "05. Supplier Payables Network", desc: "Vendor payment terms, schedule tracking, and early payment discount calculations." }
        ]
      },
      {
        title: "Financial Ledgers & Treasury (Ch 06 - 10)",
        badge: "QUADRANT II // LEDGERS & STATEMENTS",
        tone: "matcha",
        items: [
          { label: "06. Double-Entry Journal", desc: "Atomic general ledger, automated debit/credit balancing, and voucher history." },
          { label: "07. Cash & Bank Treasury", desc: "Opening-to-closing cash bridge, bank reconciliation, and liquid capital reserves." },
          { label: "08. Expense Controller", desc: "Operating burn categorization, voucher attachments, and budget threshold tracking." },
          { label: "09. GST & Tax Compliance Engine", desc: "Input Tax Credit (ITC) reconciliation, GSTR-1/3B schedules, and tax liability." },
          { label: "10. Financial Statements", desc: "Dynamic Profit & Loss statements, Balance Sheets, and Trial Balance generation." }
        ]
      },
      {
        title: "Intelligence & Scenario Lab (Ch 11 - 14)",
        badge: "QUADRANT III // PREDICTIVE COGNITION",
        tone: "gold",
        items: [
          { label: "11. DuPont Profitability Analytics", desc: "Decomposes ROE into Profit Margin, Asset Turnover, and Financial Leverage." },
          { label: "12. What-If Scenario Laboratory", desc: "Stress-test inflation shocks, supply disruptions, and customer credit defaults." },
          { label: "13. Working Capital Goal Planner", desc: "Target runway modeling, receivables reduction plans, and milestone alerts." },
          { label: "14. Constellation Topology Visualizer", desc: "Interactive node graph mapping party payment networks and systemic credit risks." }
        ]
      },
      {
        title: "Governance, RBAC & Audit (Ch 15 - 18)",
        badge: "QUADRANT IV // GOVERNANCE & SECURITY",
        tone: "ink",
        items: [
          { label: "15. Staged AI Decision Copilot", desc: "Context-aware operational assistant operating in read-only analysis mode." },
          { label: "16. Immutable Audit Trail", desc: "Cryptographic log recording every create, update, delete, and login event." },
          { label: "17. Multi-Tenant Organization RBAC", desc: "Role-based access control (Owner, Admin, Accountant, Viewer) and tenant isolation." },
          { label: "18. System Settings & Telemetry", desc: "Workspace preferences, API webhook configurations, and database health metrics." }
        ]
      }
    ]
  },

  // SLIDE 05
  {
    id: 5,
    category: "Architectural Decoupling & Inversion",
    title: "Clean Architecture & Domain-Driven Design (DDD)",
    subtitle: "The Dependency Inversion Rule: Business logic has zero external dependencies on databases, UI frameworks, or third-party SDKs.",
    layout: "quad",
    cards: [
      {
        title: "1. Domain Core",
        badge: "PURE BUSINESS LOGIC",
        tone: "crimson",
        items: [
          { label: "Entities & Aggregates", desc: "Invoice, StockLot, JournalEntry containing core business state and integrity invariants." },
          { label: "Value Objects", desc: "Money, GSTIN, TaxRate ensuring immutable attribute validity and mathematical correctness." },
          { label: "Domain Events", desc: "InvoiceIssued, StockDepleted signaling significant lifecycle occurrences." },
          { label: "Zero Dependencies", desc: "Strictly zero imports from FastAPI, SQLAlchemy, or external network packages." }
        ]
      },
      {
        title: "2. Application Layer",
        badge: "USE CASES & WORKFLOWS",
        tone: "gold",
        items: [
          { label: "Use-Case Interactors", desc: "PostInvoiceUseCase, ReconcileKhataUseCase, DepleteLotUseCase orchestrating business flows." },
          { label: "Unit of Work Contract", desc: "Abstract transactional boundaries ensuring atomic multi-repository writes." },
          { label: "CQRS Segregation", desc: "Command handlers execute mutations; query services fetch read-only projections." },
          { label: "Orchestration", desc: "Coordinates domain entities to complete complete commercial workflows without leaks." }
        ]
      },
      {
        title: "3. Infrastructure Layer",
        badge: "ADAPTERS & PERSISTENCE",
        tone: "matcha",
        items: [
          { label: "Repository Adapters", desc: "Concrete SQLAlchemy repository implementations satisfying domain port interfaces." },
          { label: "Database ORM", desc: "Maps SQL tables to pure domain entities without exposing persistence schemas." },
          { label: "External Gateways", desc: "Resend SMTP email dispatcher, PDF generators, and external AI connectors." },
          { label: "Swappable", desc: "Database can be swapped from PostgreSQL to SQLite without touching domain logic." }
        ]
      },
      {
        title: "4. Presentation Layer",
        badge: "REST API & INTERFACE",
        tone: "ink",
        items: [
          { label: "FastAPI Controllers", desc: "Dependency-injected route endpoints serializing input JSON requests and responses." },
          { label: "Next.js Client", desc: "TypeScript user interface leveraging design tokens, Tailwind, and Framer Motion." },
          { label: "Security Gateway", desc: "JWT authentication, tenant scoping, and role-based permissions." },
          { label: "Audit Middleware", desc: "Intercepts inbound requests and streams trace telemetry to audit tables." }
        ]
      }
    ]
  },

  // SLIDE 06
  {
    id: 6,
    category: "Fundamental OOP Principles",
    title: "OOM Core: Classes, Objects, Attributes & Immutability",
    subtitle: "How we architected fundamental object structures to enforce strict financial validity at instantiation time.",
    layout: "tri",
    cards: [
      {
        title: "Money: Immutable Value Object",
        badge: "VALUE OBJECT BLUEPRINT",
        tone: "crimson",
        items: [
          { label: "Design Aim", desc: "Represent all monetary figures as an immutable value object wrapping an integer paise count." },
          { label: "Constructor Validation", desc: "The initialization constructor validates scale factor (10^2) and rejects negative values or floats." },
          { label: "Attribute Immutability", desc: "Fields are declared read-only. Mutation methods return brand new Money instances." },
          { label: "Operator Overloading", desc: "Implements polymorphic __add__, __sub__, and __mul__ with currency type checking." },
          { label: "Equality Contract", desc: "Two Money objects are equal if and only if their paise values and currency codes match exactly." }
        ]
      },
      {
        title: "Invoice: Aggregate Root",
        badge: "AGGREGATE ROOT BLUEPRINT",
        tone: "matcha",
        items: [
          { label: "Design Aim", desc: "Serve as the consistency boundary and aggregate root for all line-item commercial transactions." },
          { label: "Encapsulated State", desc: "Manages internal line lists, tax subtotals, issue timestamps, and customer relationships." },
          { label: "Guarded Construction", desc: "Factory constructor requires at least one valid line item, rejecting zero-value invoices." },
          { label: "Lifecycle Invariants", desc: "Disallows modifications to line items once the invoice transitions out of DRAFT status." },
          { label: "Total Derivation", desc: "Total gross amount is derived dynamically by summing individual line totals, preventing cached drift." }
        ]
      },
      {
        title: "StockLot: Discrete Entity",
        badge: "DOMAIN ENTITY BLUEPRINT",
        tone: "gold",
        items: [
          { label: "Design Aim", desc: "Track discrete inward inventory batches to enable precise First-In, First-Out depletion." },
          { label: "Identity & State", desc: "Maintains unique batch UUID, supplier inward voucher reference, and acquisition date." },
          { label: "Quantity Partitioning", desc: "Tracks original purchase quantity and remaining available quantity independently." },
          { label: "State Transition", desc: "Exposes controlled deplete(qty) method ensuring remaining stock cannot drop below zero." },
          { label: "Batch Valuation", desc: "Maintains exact per-unit acquisition cost in paise throughout its entire lifecycle." }
        ]
      }
    ]
  },

  // SLIDE 07
  {
    id: 7,
    category: "Information Hiding & Contract Design",
    title: "OOM Pillar: Encapsulation & Abstraction",
    subtitle: "Shielding business invariants behind private attributes and abstract repository interfaces.",
    layout: "split",
    cards: [
      {
        title: "Encapsulation: Information Hiding & State Guarding",
        badge: "INFORMATION HIDING & INTEGRITY",
        tone: "crimson",
        items: [
          { label: "Private Attribute Protection", desc: "Critical attributes such as ledger balances, remaining lot quantities, and line items are private and inaccessible for direct external mutation." },
          { label: "Mutation Gateways", desc: "External actors must call explicit public domain methods such as record_payment() or allocate_stock(), which validate all business rules first." },
          { label: "State Machine Invariant Enforcement", desc: "An invoice cannot jump from DRAFT to PAID without passing through ISSUED and recording an atomic ledger voucher." },
          { label: "Self-Validating Aggregates", desc: "The CustomerKhata aggregate maintains its current balance internally, recomputing against verified journal entries rather than trusting client-supplied balance inputs." },
          { label: "Outcome", desc: "Eliminates side-effect bugs, accidental state corruption, and race conditions across multi-tenant operations." }
        ]
      },
      {
        title: "Abstraction: Interface Contracts & Decoupling",
        badge: "CONTRACT DESIGN & SEPARATION",
        tone: "matcha",
        items: [
          { label: "Abstract Repository Ports", desc: "Application use-cases interact with abstract interfaces (ILedgerRepository, IInventoryRepository, IInvoiceRepository) rather than database drivers." },
          { label: "Hiding Persistence Mechanisms", desc: "Domain services remain completely unaware whether data is stored in PostgreSQL, SQLite, or an in-memory dictionary during unit testing." },
          { label: "Separation of What vs How", desc: "The domain layer defines what capabilities are required; the infrastructure layer provides how those capabilities are executed." },
          { label: "Third-Party Abstraction", desc: "AI reasoning models and email dispatchers are hidden behind IAICopilotClient and IEmailService interfaces." },
          { label: "Outcome", desc: "High modularity, painless unit testing via mock injection, and zero database lock-in." }
        ]
      }
    ]
  },

  // SLIDE 08
  {
    id: 8,
    category: "Class Hierarchies & Dynamic Dispatch",
    title: "OOM Pillar: Inheritance & Polymorphism",
    subtitle: "Maximizing code reuse through structural inheritance and runtime polymorphic strategy dispatch.",
    layout: "split",
    cards: [
      {
        title: "Class Inheritance Hierarchies",
        badge: "STRUCTURAL INHERITANCE",
        tone: "crimson",
        items: [
          { label: "BaseEntity Abstract Class", desc: "Provides shared identity fields: UUID id, organization_id for multi-tenancy, created_at, updated_at, and version for optimistic locking." },
          { label: "BaseEvent Hierarchy", desc: "Common BaseDomainEvent extended by InvoiceIssuedEvent, PaymentReceivedEvent, and StockDepletedEvent for decoupled internal message pub/sub." },
          { label: "BaseVoucher Specialization", desc: "Abstract Voucher class extended into SalesInvoiceVoucher, PurchaseBillVoucher, and BankTransferVoucher with specialized debit/credit posting logic." },
          { label: "Template Method Inheritance", desc: "Base reporting class implements the skeleton workflow for statement exports while subclasses implement format-specific cell formatting." },
          { label: "Architectural Goal", desc: "DRY (Don't Repeat Yourself) principle enforced across audit trails and multi-tenant security layers." }
        ]
      },
      {
        title: "Polymorphic Strategy Dispatch",
        badge: "RUNTIME POLYMORPHISM",
        tone: "gold",
        items: [
          { label: "Discount Calculation Strategy", desc: "The invoice pricing engine interacts with a polymorphic IDiscountStrategy interface without branching or conditionals." },
          { label: "Concrete Strategies", desc: "Implemented via FixedAmountDiscount and PercentageDiscount, each computing discount deductions dynamically at runtime." },
          { label: "Tax Engine Polymorphism", desc: "ITaxRule interface dynamically dispatches computation between Intra-State GST (CGST + SGST) and Inter-State GST (IGST) based on party state codes." },
          { label: "Scenario Simulation Shocks", desc: "The What-If laboratory dispatches an array of polymorphic IScenarioShock objects (InflationShock, SupplyDelayShock, CreditDefaultShock) across financial models." },
          { label: "Architectural Goal", desc: "Seamless extensibility for new tax laws and commercial terms without modifying core order processing pipelines." }
        ]
      }
    ]
  },

  // SLIDE 09
  {
    id: 9,
    category: "Structural Object Topology",
    title: "Object Relationships: Composition, Aggregation & Association",
    subtitle: "Designing clear lifecycle bindings and dependency strengths between commercial domain objects.",
    layout: "quad",
    cards: [
      {
        title: "Composition (◆)",
        badge: "LIFECYCLE DEPENDENCY",
        tone: "crimson",
        items: [
          { label: "Invoice & InvoiceLine", desc: "An InvoiceLine has no independent existence outside its parent Invoice aggregate root." },
          { label: "Cascade Deletion", desc: "Deleting or rolling back an invoice cascades destruction to all child line items automatically." },
          { label: "Ownership Boundary", desc: "The invoice aggregate exclusively manages the creation and removal of its line items." },
          { label: "Integrity Guarantee", desc: "Orphaned invoice line items are mathematically impossible in the domain model." }
        ]
      },
      {
        title: "Aggregation (◇)",
        badge: "CONTAINMENT WITHOUT LIFECYCLE",
        tone: "gold",
        items: [
          { label: "Organization & Warehouse", desc: "An Organization aggregates multiple Warehouse facilities across operational regions." },
          { label: "Independent Lifecycle", desc: "Warehouses retain their historical inventory records and ledger references even if organization structures evolve." },
          { label: "Shared Reference", desc: "A warehouse exists as an independent entity in physical space, referenced by multiple operational entities." },
          { label: "Decoupled Evolution", desc: "Allows reassigning warehouses across business units without breaking audit logs." }
        ]
      },
      {
        title: "Association (→)",
        badge: "PEER REFERENCE COUPLING",
        tone: "matcha",
        items: [
          { label: "Customer & JournalEntry", desc: "Customers are associated with journal entries via foreign UUID references." },
          { label: "Loose Coupling", desc: "Neither object owns the other. Both exist independently within their own bounded contexts." },
          { label: "Ledger Preservation", desc: "Deactivating or archiving a customer never alters historical journal entry records." },
          { label: "Audit Stability", desc: "Financial ledgers remain permanent historical records regardless of party status changes." }
        ]
      },
      {
        title: "Dependency (-->)",
        badge: "TRANSIENT METHOD CALLS",
        tone: "ink",
        items: [
          { label: "Service & Calculations", desc: "InvoiceService depends on GSTCalculationService only during validation calls." },
          { label: "No State Retention", desc: "The service receives tax parameters and returns calculated tax lines without retaining long-term references." },
          { label: "Parameter Passing", desc: "Dependencies are passed into specific method arguments rather than held as permanent object state." },
          { label: "Memory Efficiency", desc: "Allows lightweight stateless services to scale horizontally under high request loads." }
        ]
      }
    ]
  },

  // SLIDE 10
  {
    id: 10,
    category: "Object-Oriented Design Principles",
    title: "SOLID Principles in Action: SRP, OCP & LSP",
    subtitle: "Applying foundational SOLID design principles to construct maintainable, enterprise-grade software.",
    layout: "tri",
    cards: [
      {
        title: "Single Responsibility (SRP)",
        badge: "SRP // RESPONSIBILITY ISOLATION",
        tone: "crimson",
        items: [
          { label: "Principle Definition", desc: "A class should have one, and only one, reason to change." },
          { label: "InvoiceValidator", desc: "Solely responsible for GST tax rules, HSN validation, and schema checks." },
          { label: "FIFOEngine", desc: "Solely responsible for inventory lot tracking, queue ordering, and COGS calculations." },
          { label: "LedgerPostingService", desc: "Solely responsible for generating balanced debit/credit double-entry vouchers." },
          { label: "Architectural Benefit", desc: "Changes to tax calculation logic never risk introducing regressions into inventory depletion or ledger engines." }
        ]
      },
      {
        title: "Open/Closed Principle (OCP)",
        badge: "OCP // EXTENSION WITHOUT REGRESSION",
        tone: "matcha",
        items: [
          { label: "Principle Definition", desc: "Software entities should be open for extension, but closed for modification." },
          { label: "What-If Simulator", desc: "The scenario analysis engine is designed to accept arbitrary financial disruption models without altering the core simulation loop." },
          { label: "Extensible Shocks", desc: "Developers can introduce new scenario transformers (TariffShock, SupplyDelay) simply by implementing the IScenarioShock contract." },
          { label: "Export Pipeline", desc: "The reporting engine supports new export formats (CSV, PDF, Excel) through pluggable formatter strategies without changing report data generators." },
          { label: "Architectural Benefit", desc: "Core accounting models remain stable and production-proven while business capabilities expand." }
        ]
      },
      {
        title: "Liskov Substitution (LSP)",
        badge: "LSP // BEHAVIORAL COMPLIANCE",
        tone: "gold",
        items: [
          { label: "Principle Definition", desc: "Subtypes must be substitutable for their base types without altering program correctness." },
          { label: "Repository Contracts", desc: "Domain services interact with abstract repository types. Both SqlAlchemyLedgerRepository and InMemoryLedgerRepository conform to exact same behavioral invariants." },
          { label: "No Contract Violations", desc: "Mock repositories in automated test suites enforce identical transaction guarantees and error handling as production PostgreSQL adapters." },
          { label: "Uniform Exception Hierarchies", desc: "All repository subclasses raise domain-specific exceptions (EntityNotFoundError, ConcurrencyConflictError) rather than leaky ORM exceptions." },
          { label: "Architectural Benefit", desc: "High test speed and test fidelity with 100% test interchangeability." }
        ]
      }
    ]
  },

  // SLIDE 11
  {
    id: 11,
    category: "Interface Design & Dependency Inversion",
    title: "SOLID Principles in Action: ISP & DIP",
    subtitle: "Fine-grained client interfaces and framework-agnostic dependency injection wiring.",
    layout: "split",
    cards: [
      {
        title: "Interface Segregation Principle (ISP)",
        badge: "ISP // CLIENT INTERFACE PRECISION",
        tone: "crimson",
        items: [
          { label: "Principle Definition", desc: "Clients should not be forced to depend upon interfaces they do not use." },
          { label: "IReadableKhataRepository", desc: "Exposes only query methods (get_by_id, list_transactions_for_party) for read-heavy dashboard and reporting controllers." },
          { label: "IWritableKhataRepository", desc: "Exposes mutation methods (append_voucher, commit_journal_batch) required only by transactional posting services." },
          { label: "IAuditableRepository", desc: "Specialized contract for compliance and telemetry auditors requiring cryptographic log access." },
          { label: "Architectural Benefit", desc: "Read-only reporting services cannot accidentally invoke write methods, enforcing structural security boundaries across the entire system." }
        ]
      },
      {
        title: "Dependency Inversion Principle (DIP)",
        badge: "DIP // INVERTED CONTROL & MOCKABILITY",
        tone: "matcha",
        items: [
          { label: "Principle Definition", desc: "High-level modules should not depend on low-level modules; both should depend on abstractions." },
          { label: "Inverted Flow of Control", desc: "Domain use-cases (IssueInvoiceUseCase) depend exclusively on domain port interfaces. Concrete database drivers and external API connectors depend on the domain." },
          { label: "FastAPI Dependency Injection", desc: "The application bootstrap layer configures runtime dependency injection, injecting PostgreSQL session factories and Redis cache adapters into service constructors." },
          { label: "Zero ORM Coupling", desc: "If PostgreSQL is swapped for an alternative datastore, exactly zero lines of domain logic or business validation require modification." },
          { label: "Architectural Benefit", desc: "True framework independence, frictionless test mocking, and sustainable multi-decade codebase maintainability." }
        ]
      }
    ]
  },

  // SLIDE 12
  {
    id: 12,
    category: "Software Design Patterns Taxonomy",
    title: "Enterprise Software Design Patterns: 23 Patterns Catalog",
    subtitle: "A rigorous catalog of Gang of Four (GoF) and enterprise architectural patterns implemented across the codebase.",
    layout: "tri",
    cards: [
      {
        title: "Creational Patterns (5)",
        badge: "CREATIONAL ARCHITECTURE",
        tone: "crimson",
        items: [
          { label: "Factory Method", desc: "Instantiates specialized financial vouchers (SalesVoucher, ExpenseVoucher) based on commercial transaction types." },
          { label: "Abstract Factory", desc: "Creates cohesive families of repository adapters configured for production PostgreSQL vs in-memory test environments." },
          { label: "Builder Pattern", desc: "Constructs complex multi-line GST invoices with step-by-step validation of customer data, lines, and tax rules." },
          { label: "Singleton Pattern", desc: "Manages the centralized database connection pool and application configuration environment singleton." },
          { label: "Prototype Pattern", desc: "Clones baseline financial scenario states for rapid in-memory What-If Monte Carlo simulation branching." }
        ]
      },
      {
        title: "Structural Patterns (7)",
        badge: "STRUCTURAL ARCHITECTURE",
        tone: "matcha",
        items: [
          { label: "Adapter Pattern", desc: "Transforms raw third-party banking and GST portal payloads into internal normalized domain models." },
          { label: "Facade Pattern", desc: "Provides a simplified FinancialOverviewFacade unifying accounts receivable, payable, and cash runway data." },
          { label: "Composite Pattern", desc: "Models hierarchical Chart of Accounts (Assets -> Current Assets -> Bank Accounts -> HDFC Primary)." },
          { label: "Decorator Pattern", desc: "Wraps repository calls with execution timers, automated caching, and cryptographic audit logging." },
          { label: "Proxy Pattern", desc: "Enforces multi-tenant data isolation and role-based permissions before queries hit the database." },
          { label: "Bridge Pattern", desc: "Decouples financial report data extractors from presentation renderers (PDF, CSV, HTML)." },
          { label: "Flyweight Pattern", desc: "Shares immutable tax rate schedules and HSN reference tables across thousands of concurrent invoice lines." }
        ]
      },
      {
        title: "Behavioral Patterns (11)",
        badge: "BEHAVIORAL ARCHITECTURE",
        tone: "gold",
        items: [
          { label: "Strategy Pattern", desc: "Pluggable tax and discount calculation engines selected dynamically at runtime." },
          { label: "Observer Pattern", desc: "Domain event publisher notifying Khata, inventory, and analytics listeners upon invoice issuance." },
          { label: "Command Pattern", desc: "Encapsulates ledger postings as executable commands supporting automated rollback." },
          { label: "State Pattern", desc: "Governs invoice transitions (DRAFT -> ISSUED -> PARTIALLY_PAID -> PAID -> VOID)." },
          { label: "Memento Pattern", desc: "Captures working capital snapshots allowing users to revert What-If scenario experiments." },
          { label: "Chain of Responsibility", desc: "Sequences inbound request validation: Auth -> Tenant -> Schema -> Business Rules." },
          { label: "Template Method", desc: "Standardizes statement export structure while subclasses format individual document rows." },
          { label: "Iterator Pattern", desc: "Traverses discrete FIFO inventory lots chronologically for optimal cost depletion." },
          { label: "Mediator Pattern", desc: "Central event bus decoupling UI view updates from backend WebSocket notifications." },
          { label: "Visitor Pattern", desc: "Traverses account hierarchies to accumulate balance sheet totals and calculate financial ratios." },
          { label: "Interpreter Pattern", desc: "Evaluates user-defined financial formula expressions inside the goal modeling engine." }
        ]
      }
    ]
  },

  // SLIDE 13
  {
    id: 13,
    category: "Deterministic Core Engineering",
    title: "Financial Sovereignty: Integer-Paisa Khata & FIFO Engine",
    subtitle: "Eliminating mathematical drift and costing distortion through pure integer arithmetic and queue theory.",
    layout: "split",
    cards: [
      {
        title: "Double-Entry Khata Balancing Mechanics",
        badge: "LEDGER DETERMINISM // DOUBLE-ENTRY",
        tone: "crimson",
        items: [
          { label: "Pure Integer Paisa Storage", desc: "All monetary quantities are scaled by 100 and stored as 64-bit integers (BIGINT). A value of ₹1,450.50 is stored strictly as 145050 paise." },
          { label: "Algebraic Balance Law", desc: "Every commercial event decomposes into balancing debits and credits: Sales Invoice debits Customer Receivables (+₹11,800), credits Revenue (-₹10,000), credits GST (-₹1,800)." },
          { label: "Sum-to-Zero Verification", desc: "Before committing to disk, the ledger engine verifies: Sum(Debits) - Sum(Credits) == 0. An assertion failure aborts the entire transaction." },
          { label: "Multi-Party Reconciliation", desc: "Customer statements and supplier ledgers reconcile instantly down to the exact paisa with complete voucher drill-down." },
          { label: "Audit Reconciliation", desc: "Eliminates fractional-cent accumulation over time, guaranteeing audit-grade reconciliation with bank and GST records." }
        ]
      },
      {
        title: "Perpetual FIFO Queue Costing Mechanics",
        badge: "INVENTORY DETERMINISM // FIFO QUEUE",
        tone: "matcha",
        items: [
          { label: "Batch Lot Allocation", desc: "Each inward purchase bill enqueues a new StockLot record with quantity, acquisition date, and unit cost in paise." },
          { label: "Chronological Depletion Queue", desc: "When a sale occurs, the FIFO engine dequeues from the oldest unexhausted lot first." },
          { label: "Lot Splitting Logic", desc: "If an order exceeds the remaining quantity of the oldest lot, the engine depletes that lot to zero, computes its partial COGS, and consumes the remaining balance from the next oldest lot." },
          { label: "Exact Margin Proof", desc: "Gross margin is computed per individual invoice line against actual batch purchase prices, exposing true profitability rather than estimated averages." },
          { label: "Inventory Valuation", desc: "Balance sheet inventory value is always equal to the exact sum of remaining unexhausted lots." }
        ]
      }
    ]
  },

  // SLIDE 14
  {
    id: 14,
    category: "AI Safety & Two-Person Control",
    title: "Human-in-the-Loop AI & Staged Governance Engine",
    subtitle: "Preventing autonomous hallucinations from mutating financial records through multi-stage approval state machines.",
    layout: "split",
    cards: [
      {
        title: "Read-Only DAG Investigation Engine",
        badge: "COGNITIVE ISOLATION // ZERO WRITE PERMISSION",
        tone: "gold",
        items: [
          { label: "Zero Write Access", desc: "The AI Financial Copilot operates within a strictly sandboxed read-only tool environment." },
          { label: "Tool DAG Architecture", desc: "The copilot issues queries via isolated tools: get_aging_receivables(), check_stock_velocity(), and simulate_cash_runway()." },
          { label: "Deterministic RAG Context", desc: "AI prompts are grounded in live, verified ledger data extracted directly from the double-entry Khata, preventing hallucinated numbers." },
          { label: "Transparent Reasoning", desc: "Every recommendation generated by the model includes verifiable data citations and operational rationale." },
          { label: "Safety Guarantee", desc: "The model cannot execute database updates, write SQL queries, or initiate disbursements autonomously." }
        ]
      },
      {
        title: "Staged Action State Machine & Dual Control",
        badge: "GOVERNANCE GATE // STATE MACHINE CONTROL",
        tone: "crimson",
        items: [
          { label: "Structured Action Proposals", desc: "When the AI suggests an action (e.g., supplier restock or credit freeze), it creates an immutable ProposedAction record." },
          { label: "Finite State Machine Flow", desc: "Proposals progress through strict state gates: PROPOSED -> REVIEWED -> CONFIRMED -> EXECUTED." },
          { label: "Human-in-the-Loop Confirmation", desc: "An authorized human operator must inspect the proposal, review impact metrics, and click Confirm to authorize execution." },
          { label: "Dual-Control Verification", desc: "Critical financial actions (e.g., debt write-offs above threshold) enforce multi-person authorization from distinct user accounts." },
          { label: "Cryptographic Audit Trail", desc: "All executed actions are sealed with operator ID, client IP, timestamp, and SHA-256 hash in append-only audit tables." }
        ]
      }
    ]
  },

  // SLIDE 15
  {
    id: 15,
    category: "Empirical Verification & Project Evaluation",
    title: "Academic Handover, Test Verification & Artifacts",
    subtitle: "Complete verification evidence across 194 automated test suites, production deployments, and UML documentation.",
    layout: "split",
    cards: [
      {
        title: "Automated Test Suite Verification",
        badge: "EMPIRICAL TEST SUITE // 100% PASSING",
        tone: "matcha",
        items: [
          { label: "Backend Pytest Suite", desc: "164 PASSED (100% green). Comprehensive test coverage spanning domain models, integer-paisa math, FIFO lot queues, IDOR tenant security boundaries, and API routes." },
          { label: "Frontend Vitest Suite", desc: "22 PASSED (100% green). Unit verification of atomic visual components, currency formatting, state management, and form validation." },
          { label: "Playwright E2E User Journeys", desc: "8 of 8 PASSED. Automated end-to-end browser journeys validating sales issuance, inventory depletion, Khata balancing, and AI confirmation flows." },
          { label: "Code Quality & Linting", desc: "Full compliance with strict ESLint and Black/Ruff styling guidelines with zero warnings or circular dependencies." },
          { label: "OOM Course Fulfillment", desc: "Rigorous fulfillment of all OOM syllabus requirements: encapsulation, inheritance, polymorphism, SOLID, 23 design patterns, and robust exception design." }
        ]
      },
      {
        title: "Repository Artifacts & Complete UML Notice",
        badge: "ACADEMIC DELIVERABLES & UML REPOSITORY",
        tone: "crimson",
        items: [
          { label: "GitHub Repository", desc: "Official source code repository: https://github.com/ayush-mg/arthlens" },
          { label: "UML Specification Notice", desc: "As required, raw UML diagrams are omitted from this deck. Complete, high-fidelity formal UML specifications are thoroughly documented in the project repository and README.md:" },
          { label: "• Domain Class Diagram", desc: "Full class model with attributes, methods, visibility markers, stereotypes, and cardinality." },
          { label: "• System Use-Case Architecture", desc: "Primary actors (Owner, Accountant, Auditor, AI) and functional boundaries." },
          { label: "• Sequence Diagrams", desc: "Order-to-Ledger unit-of-work pipeline and AI Staged Investigation flow." },
          { label: "• State Machine Diagrams", desc: "Invoice commercial lifecycle and AI Action governance state transitions." },
          { label: "Live Deployments", desc: "Frontend Web: https://arthlens-two.vercel.app  |  Backend API: https://arthlens-n6ah.onrender.com" }
        ]
      }
    ]
  }
];

export default function PresentationPage() {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isAutoplay, setIsAutoplay] = useState(false);

  const currentSlide = SLIDES[currentSlideIndex];

  const nextSlide = useCallback(() => {
    setCurrentSlideIndex((prev) => (prev < SLIDES.length - 1 ? prev + 1 : 0));
  }, []);

  const prevSlide = useCallback(() => {
    setCurrentSlideIndex((prev) => (prev > 0 ? prev - 1 : SLIDES.length - 1));
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        nextSlide();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        prevSlide();
      } else if (e.key.toLowerCase() === "f") {
        toggleFullscreen();
      } else if (e.key >= "1" && e.key <= "9") {
        const target = parseInt(e.key) - 1;
        if (target < SLIDES.length) setCurrentSlideIndex(target);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [nextSlide, prevSlide]);

  useEffect(() => {
    if (!isAutoplay) return;
    const interval = setInterval(nextSlide, 10000);
    return () => clearInterval(interval);
  }, [isAutoplay, nextSlide]);

  // Ensure solid website background
  useEffect(() => {
    const origHtmlBg = document.documentElement.style.backgroundColor;
    const origBodyBg = document.body.style.backgroundColor;
    document.documentElement.style.backgroundColor = "#FAF7F2";
    document.body.style.backgroundColor = "#FAF7F2";
    return () => {
      document.documentElement.style.backgroundColor = origHtmlBg;
      document.body.style.backgroundColor = origBodyBg;
    };
  }, []);

  const getToneBorder = (tone?: "crimson" | "matcha" | "gold" | "ink") => {
    switch (tone) {
      case "crimson":
        return "border-l-4 border-l-[#C8281E]";
      case "matcha":
        return "border-l-4 border-l-[#2D7D52]";
      case "gold":
        return "border-l-4 border-l-[#D4A359]";
      default:
        return "border-l-4 border-l-[#231412]";
    }
  };

  const getBadgeColor = (tone?: "crimson" | "matcha" | "gold" | "ink") => {
    switch (tone) {
      case "crimson":
        return "text-[#C8281E]";
      case "matcha":
        return "text-[#2D7D52]";
      case "gold":
        return "text-[#D4A359]";
      default:
        return "text-[#231412]";
    }
  };

  return (
    <div className="fixed inset-0 z-50 w-screen h-screen bg-[#FAF7F2] text-[#231412] flex flex-col font-sans select-none overflow-hidden">
      {/* Top Tactical Control Bar */}
      <header className="h-14 border-b border-[#231412]/15 bg-[#FAF7F2] px-6 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex items-center space-x-2 text-xs font-mono font-bold tracking-widest text-[#231412] hover:text-[#C8281E] transition-colors"
          >
            <span>ARTH</span>
            <span className="text-[#C8281E]">LENS</span>
            <span className="px-1.5 py-0.5 bg-[#FAF7F2] border border-[#C8281E]/30 text-[#C8281E] text-[10px]">
              ■ °01
            </span>
          </Link>
          <span className="text-[#231412]/30">|</span>
          <span className="text-xs font-mono font-bold tracking-wider text-[#C8281E] uppercase">
            {currentSlide.category}
          </span>
        </div>

        {/* Slide Counter & Jump Pills */}
        <div className="hidden md:flex items-center space-x-1">
          {SLIDES.map((s, idx) => (
            <button
              key={s.id}
              onClick={() => setCurrentSlideIndex(idx)}
              className={`w-6 h-6 text-[10px] font-mono font-bold transition-all border ${
                currentSlideIndex === idx
                  ? "bg-[#C8281E] text-white border-[#C8281E]"
                  : "bg-white text-[#231412]/60 border-[#231412]/15 hover:border-[#C8281E]/50 hover:text-[#231412]"
              }`}
            >
              {s.id}
            </button>
          ))}
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsAutoplay(!isAutoplay)}
            className={`p-1.5 text-xs font-mono border transition-colors flex items-center space-x-1 ${
              isAutoplay
                ? "bg-[#2D7D52] text-white border-[#2D7D52]"
                : "bg-white text-[#231412]/70 border-[#231412]/20 hover:text-[#231412]"
            }`}
            title="Toggle Autoplay (10s)"
          >
            {isAutoplay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-1.5 text-xs font-mono border border-[#231412]/20 bg-white text-[#231412]/70 hover:text-[#231412] transition-colors"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <div className="px-2.5 py-1 bg-white border border-[#231412]/20 text-xs font-mono font-bold text-[#231412]">
            {String(currentSlide.id).padStart(2, "0")} / 15
          </div>
        </div>
      </header>

      {/* Main Slide Presentation Stage */}
      <main className="flex-1 relative overflow-hidden flex flex-col justify-between p-6 md:p-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentSlide.id}
            initial={{ opacity: 0, x: 25 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -25 }}
            transition={{ duration: 0.28, ease: "easeInOut" }}
            className="flex-1 flex flex-col justify-between max-w-7xl mx-auto w-full"
          >
            {/* Slide Header */}
            <div className="mb-4">
              <div className="flex items-center space-x-3 mb-1">
                <span className="text-xs font-mono font-bold text-[#C8281E] uppercase tracking-wider">
                  ARTHLENS // {currentSlide.category}
                </span>
                {currentSlide.badge && (
                  <span className="px-2 py-0.5 bg-[#FAF7F2] border border-[#D4A359] text-[#D4A359] text-[10px] font-mono font-bold">
                    {currentSlide.badge}
                  </span>
                )}
              </div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-[#231412] tracking-tight">
                {currentSlide.title}
              </h1>
              <p className="text-sm text-[#5C403B] italic mt-1 font-sans">
                {currentSlide.subtitle}
              </p>

              {currentSlide.equation && (
                <div className="mt-3 p-2.5 bg-[#F3ECE3] border border-[#C8281E]/40 text-center font-mono text-xs font-bold text-[#C8281E]">
                  {currentSlide.equation}
                </div>
              )}
            </div>

            {/* Slide Cards Content Grid */}
            <div
              className={`flex-1 grid gap-4 items-stretch ${
                currentSlide.layout === "title"
                  ? "grid-cols-1 md:grid-cols-3"
                  : currentSlide.layout === "split"
                  ? "grid-cols-1 md:grid-cols-2"
                  : currentSlide.layout === "quad"
                  ? "grid-cols-1 md:grid-cols-2"
                  : "grid-cols-1 md:grid-cols-3"
              }`}
            >
              {currentSlide.cards.map((card, idx) => (
                <div
                  key={idx}
                  className={`bg-white border border-[#231412]/15 p-4 shadow-sm flex flex-col justify-between ${getToneBorder(
                    card.tone
                  )}`}
                >
                  <div>
                    {card.badge && (
                      <div className={`text-[10px] font-mono font-bold tracking-wider mb-1 uppercase ${getBadgeColor(card.tone)}`}>
                        {card.badge}
                      </div>
                    )}
                    <h3 className="text-base font-bold text-[#231412] mb-3 pb-1.5 border-b border-[#231412]/10 font-sans">
                      {card.title}
                    </h3>

                    <div className="space-y-2">
                      {card.items.map((item, i) => (
                        <div key={i} className="text-xs leading-relaxed text-[#5C403B]">
                          <span className="font-bold text-[#231412] mr-1.5">• {item.label}:</span>
                          <span>{item.desc}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Slide Footer Note */}
            {currentSlide.footerNote && (
              <div className="mt-3 text-[11px] font-mono text-[#9A7E78] text-center border-t border-[#231412]/10 pt-2">
                {currentSlide.footerNote}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Bottom Navigation Bar */}
      <footer className="h-12 border-t border-[#231412]/15 bg-[#FAF7F2] px-6 flex items-center justify-between text-xs font-mono text-[#9A7E78] shrink-0">
        <div className="flex items-center space-x-4">
          <span>IIIT ALLAHABAD // OOM COURSE PROJECT</span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline text-[#5C403B]">AYUSH MISHRA (IIT2025108), ABHAY PRATAP SINGH (IIT2025109), MAYANK PURI (IIT2025104)</span>
        </div>

        <div className="flex items-center space-x-2">
          <span className="hidden md:inline mr-2 text-[10px] text-[#9A7E78]">
            [Use ← / → keys or Space to navigate | F for Fullscreen]
          </span>
          <button
            onClick={prevSlide}
            className="px-3 py-1 bg-white border border-[#231412]/20 text-[#231412] hover:bg-[#FAF7F2] hover:border-[#C8281E] flex items-center space-x-1 font-bold transition-colors"
          >
            <ArrowLeft className="w-3 h-3" />
            <span>PREV</span>
          </button>
          <button
            onClick={nextSlide}
            className="px-3 py-1 bg-[#C8281E] text-white border border-[#C8281E] hover:bg-[#A81E15] flex items-center space-x-1 font-bold transition-colors"
          >
            <span>NEXT</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </footer>
    </div>
  );
}
