# ArthLens Verification & Testing Strategy

**Product Name:** ArthLens — Business Operating System & Decision Intelligence Platform  
**Target Coverage:** Complete Test Automation Across Backend, Database, Security, Frontend, and E2E  
**Test Frameworks:** Pytest 9 (Backend), Vitest 1.6 (Frontend Components), Playwright 1.65 (E2E Journeys)

---

## 1. Testing Pyramid

```
           / \
          /   \     E2E Journeys (Playwright): Auth, Onboarding, Workspaces
         /     \    Contract Tests (Pytest): RBAC Matrix, Security, Credentials
        /       \   Integration Tests (Pytest): REST APIs, Repositories, Concurrency
       /         \  Frontend Component Tests (Vitest): Constellation, Business API
      /___________\ Unit Tests (Pytest): Domain Invariants, Math, Decision Graphs
```

---

## 2. Test Suites Summary

### 2.1 Backend Unit & Integration Tests (193 Tests Passing)
- **`test_business_domain.py`**: Pure invariants of `Money`, `Business`, `SalesInvoice`, `Purchase`, `Product`, `Customer`, `Supplier`, `Payment`, `Goal`.
- **`test_decision_models.py`**: Decision graph node evaluation, hard constraints, alternative ranking, NPV/payback calculations.
- **`test_financial_intelligence.py`**: Deterministic calculations of P&L, cash flow statements, working capital cycles, ageing buckets, break-even units.
- **`test_business_api.py`**: Full REST API verification for workspaces, customers, suppliers, inventory, invoices, payments, goals.
- **`test_business_repositories.py`**: Direct PostgreSQL repository operations with transaction rollbacks and data verification.
- **`test_business_transaction_integrity.py`**: Atomic multi-entity operations (e.g. issuing invoices decrements stock and increments customer receivables).
- **`test_financial_intelligence_api.py`**: Financial analytics endpoints across diverse business transaction histories.
- **`test_decision_api.py`**: Decision evaluation endpoints, sensitivity models, and Monte Carlo risk simulations.
- **`test_concurrency_and_locking.py`**: Pessimistic row locking (`FOR UPDATE`) verifying race-condition immunity during concurrent payments and stock updates.
- **`test_agent_tenant_security.py`**: Cross-tenant injection attack tests: verifying that malicious prompt arguments attempting to access another business's records fail closed.
- **`test_flagship_demonstration_journey.py`**: Complete end-to-end multi-business flagship demonstration journey validating all 4 product pillars.

### 2.2 Security & Authentication Tests (58 Tests Passing)
- **`test_auth_endpoints.py`**: Login, registration, token issuance, session pinging, password recovery.
- **`test_rbac_matrix.py`**: Verification of deny-by-default permission matrix across unauthenticated, entrepreneur, and admin roles.
- **`test_csrf_and_ip_trust.py`**: Origin verification on state-changing requests; proxy IP spoofing defense.
- **`test_production_security.py`**: Rejection of forged JWTs, role elevation attempts, and untrusted origins.
- **`test_rate_limiting.py`**: User quota reservation and daily run caps.
- **`test_credential_leakage.py`**: Zero credential leakage in git history, logs, or error responses.

### 2.3 Frontend Tests (9 Tests Passing)
- **`business-constellation.test.tsx`**: Interactive Business Constellation UI, multi-workspace galaxy rendering, status pills, role tags.
- **`business-api.test.ts`**: API client serialization, error handling, health scores, and agent investigation queries.

---

## 3. Execution Commands

```bash
# Run all backend unit, integration, and security tests:
.venv\Scripts\pytest backend\tests -v

# Run all frontend component tests:
npm --prefix frontend test

# Run Next.js production build:
npm --prefix frontend run build

# Run automated master verification script:
powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1
```
