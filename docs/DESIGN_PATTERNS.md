# ArthLens Software Design Patterns

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform  
**Architecture:** Clean Architecture + Domain-Driven Design (DDD)  
**Standard:** Gang of Four (GoF) & Modern Distributed Patterns

---

## 1. Architectural Patterns

### 1.1 Clean Architecture / Hexagonal Architecture
ArthLens enforces a strict inward dependency rule:
- **Presentation Layer**: Next.js 14, Tailwind CSS, FastAPI REST routers.
- **Application Layer**: Services (`BusinessService`), Use-Case orchestrators, Agent tool executors.
- **Domain Layer**: Pure entities (`Business`, `SalesInvoice`, `Product`), value objects (`Money`, `Percentage`), and invariant rules. Has zero framework dependencies.
- **Infrastructure Layer**: PostgreSQL repositories (`PostgresBusinessRepository`), SQLAlchemy ORM models, Google Gemini adapters, and rate limiters.

```
[Presentation: FastAPI / Next.js] 
            │
            ▼
[Application Services / Tools]
            │
            ▼
   [Domain Core (Pure)] ◀── [Infrastructure: Postgres / Gemini]
```

---

## 2. GoF Design Patterns

### 2.1 Repository Pattern
- **Interfaces**: Abstract contracts defining collection-like persistence semantics.
- **Implementations**: `PostgresBusinessRepository`, `PostgresCustomerRepository`, `PostgresSupplierRepository`, `PostgresProductRepository`, `PostgresSalesInvoiceRepository`, `PostgresPurchaseRepository`, `PostgresPaymentRepository`, `PostgresGoalRepository`, `PostgresDecisionEvaluationRepository`, `PostgresAgentSessionRepository`.
- **Benefit**: Fully separates business domain invariants from PostgreSQL SQL queries and transaction management.

### 2.2 Strategy Pattern
- **Decision Evaluation & Alternative Comparison**: Different evaluation algorithms (NPV, Payback, ROI, Hurdle Rate) implement a uniform evaluation strategy interface.
- **Risk Simulation**: Deterministic Monte Carlo simulation vs. One-At-A-Time (OAT) Sensitivity perturbation can be plugged into decision nodes seamlessly.

### 2.3 Command & Tool Pattern
- **`BusinessToolRegistry`**: In the agentic AI layer, each investigative capability (`get_cash_position`, `list_pending_receivables`, `check_inventory_shortages`, `run_decision_model`) is registered as an explicit, schema-validated tool command.
- **Execution Safety**: Tools receive typed input parameters and a mandatory `AgentExecutionContext`, preventing unauthorized cross-tenant operations.

### 2.4 Factory Pattern
- **`get_llm_client()`**: Inspects configured environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `LLM_PROVIDER`) to instantiate the appropriate LLM adapter or fail closed to `DeterministicStructuredLLMClient`.
- **`create_app()`**: Application factory configuring middleware, CORS, routers, exception handlers, and security registries.

### 2.5 Decorator & Middleware Pattern
- **Authentication & Authorization**: Fast-path token verification, cookie extraction, and dynamic RBAC checks are implemented via FastAPI `Depends()` decorators and Starlette middleware (`CSRFOriginMiddleware`, `IPTrustMiddleware`).
