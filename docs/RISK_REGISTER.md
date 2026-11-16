# ArthLens Technical Risk Register

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform  
**Governance Standard:** ISO 31000 Risk Management Framework  
**Review Cycle:** Continuous Pre-Production Assurance

---

## 1. Technical & Architecture Risk Matrix

| Risk ID | Category | Risk Description | Likelihood | Impact | Severity | Mitigation Strategy |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **RSK-01** | Security | Cross-Tenant Data Leakage (IDOR) via LLM tool parameter manipulation. | Low | Critical | **High** | Enforce immutable `AgentExecutionContext` derived from authenticated HTTP session; disallow LLM from setting `business_id` or `user_id`. |
| **RSK-02** | Financial | Arithmetic Drift / Precision Loss in financial statements and interest amortizations. | Low | Critical | **High** | Mandate 100% deterministic Python `Decimal` and integer math; zero LLM-generated financial calculations. |
| **RSK-03** | Concurrency | Double Spending / Negative Inventory during concurrent invoice or payment requests. | Medium | High | **High** | Implement pessimistic database locking (`SELECT ... FOR UPDATE`) in repository methods within atomic SQLAlchemy transactions. |
| **RSK-04** | AI Reliability | Google Gemini API Outage, Rate Limiting, or Invalid JSON generation. | Medium | Medium | **Medium** | Built-in fail-closed fallback to `DeterministicStructuredLLMClient`; comprehensive JSON fence sanitization and validation. |
| **RSK-05** | Security | Credential Exposure in logs, git history, or client bundles. | Low | Critical | **High** | `CredentialFirewall` redacting API keys and Bearer tokens in error paths; automated `test_credential_leakage.py` test suite. |
| **RSK-06** | Data Integrity | Alembic migration drift or historical migration conflict. | Low | High | **Medium** | Freeze historical migrations 001-013; append new entities strictly via migrations 014 and 015; automated migration tests. |
| **RSK-07** | Frontend | Dead UI elements or desynchronized workspace client state. | Low | High | **Medium** | Next.js 14 strict type-checking; Vitest component testing; universal loading/empty/error state guards in all views. |
