# ArthLens Project Readiness and Acceptance Status

**Status: NOT ACCEPTED FOR PRODUCTION OR PUBLIC DEPLOYMENT**

This report records implementation evidence and open gates. It is not a
qualified legal, scheme, security, hosting, or production-readiness sign-off.
The user authorized autonomous progress, but that does not create missing
primary-source evidence, independent labels, vendor authorization, deployment
credentials, or external approvals.

## Phase status

| Phase | Current status | Acceptance notes |
|---|---|---|
| P0 — Research and validation | Open / partly blocked | Source licensing/currentness, approved scheme parameters, market/name review, pilot go/no-go, and vendor/hosting terms need evidence or qualified approval. |
| P1 — Domain, ledger, and auth | Implemented and verified | Core domain, ledger, repositories, auth, and diagrams have local test evidence. Startup reliability, Docker compose, active readiness, fatal migrations, and `/health` public endpoints verified. |
| P2 — Real-data foundation and Atlas | Implemented for the documented pilot scope | Local backend/frontend checks and non-screenshot browser journeys passed. Nationwide coverage and human source gates remain distinct from implementation. |
| P3 — Computational engine | Generic finance, spatial, Monte Carlo, sensitivity, and versioned policy evaluation mechanisms implemented; real-scheme policy acceptance blocked | Deterministic finance and user-configured stochastic projections require explicit assumptions and preserve quantity-level provenance. Policy rules require steward-reviewed exact source snapshots and evidence mappings; no real scheme rule is approved, and responses are not award decisions. Golden spreadsheet references are not approved. |
| P4 — Agent orchestration | Implemented and verified | 14 production tool execution bindings strictly validated; transactional worker with atomic PostgreSQL row claiming and leases via `FOR UPDATE SKIP LOCKED` (`claim_pending_run`, migration 012), checkpoint-based crash recovery and safe resumption from step mementos without re-executing completed steps (`AgentRunOrchestrator.resume`), bounded recovery attempts (3) with explicit terminal failure (`FAILED` with `WORKER_RECOVERY_EXHAUSTED`), standalone CLI runner `scripts/run_agent_worker.py`, SSE streaming, local startup/shutdown orchestration, and 7/7 PostgreSQL integration tests in `test_durable_worker.py`. |
| P5 — End-to-end workflows | Implemented and verified | Loops A, B, and C integrated. Canonical scheme viability endpoint (`POST /scenarios/{id}/scheme-viability`) performs loan amortization, working capital projections, and topological persistence to the PostgreSQL ledger. Multi-format export (JSON/CSV/XLSX/PDF) with formula-injection escaping. Offline golden replay traces for Loops A, B, and C verified in `backend/tests/unit/test_replay_golden_traces.py` (6/6 passed). Task P5-3 automatic verifier recovery, task prioritization, status completion workflow, and owner-scoped `PATCH /agent-runs/{id}/tasks/{task_id}` verified. |
| P6 — Benchmark and evaluation | Implemented and verified | Dev and validation task schema validation (SHA-256 verified), B1–B4 benchmark system adapters with representative execution, strengthened epistemic scoring, execution runner, bootstrap statistics, and execution/regression tests verified (31/31 passed). System performance latency, duration, and cost suite verified across 30 trials with explicit ASGI in-process transport metadata (`system_performance_metrics.json`). Complete security suite covering CSRF, IP trust, IDOR scenario isolation, password security, and Git-tracked credential leakage prevention verified (27/27 passed). |
| P7 — Deployment | Local orchestration verified; preflight passed; public deployment pending hosting credentials | Offline preflight (`scripts/deployment_preflight.py` verified with 1 migration head and 5 checked keys; 9/9 tests passed), local multi-process orchestration (`run-local.ps1`, `stop-local.ps1`), Next.js production server, and all 14 Playwright E2E journeys verified. |

## Verified engineering evidence

- **Full Backend Suite**: **857 passed, 2 skipped** (live network opt-ins), **0 failed in 123.57s**.
- **Golden Replay Trace Suite**: **6 passed, 0 failed in 0.64s** (`test_replay_golden_traces.py`).
- **Security & RBAC Suite**: **49 passed, 0 failed** (`test_credential_leakage.py`, `test_production_security.py`, `test_csrf_and_ip_trust.py`, `test_idor_protection.py`, `test_password_security.py`, `test_rbac_matrix.py`, `test_registration_and_account_management.py`).
- **Benchmark Suite**: **31 passed, 0 failed in 1.48s** (`test_benchmark_evaluation.py`, `test_benchmark_tools.py`, `test_benchmark_execution.py`, `test_benchmark_regression.py`).
- **Deployment Preflight & Health Endpoints**: **12 passed, 0 failed in 0.52s** (`test_deployment_preflight.py`, `test_health_endpoints.py`).
- **Frontend Vitest Suite**: **42 passed across 10 test files in 4.01s**.
- **Next.js Production Build**: **10/10 static pages compiled successfully** with zero errors.
- **Playwright E2E Suite**: **14/14 tests passed** across all 3 journey specs:
  - `e2e/user-journeys.spec.ts`: **11/11 passed in 49.5s** (covers Route Architecture, Geographic Discovery across 800 baseline districts, Pilot vs missing geometry visualization, real Census DS-05 economic indicators, Provenance Drawer epistemic attributes, Cytoscape DAG controls, 3-role RBAC matrix, responsive multi-viewport screenshots, narrative sequence, and fail-closed typed APIs).
  - `e2e/auth-journey.spec.ts`: **2/2 passed** (covers registration, login, cookie persistence, password recovery, and cross-user IDOR isolation).
  - `e2e/complete-user-journey.spec.ts`: **1/1 passed** (covers complete end-to-end user workflow).
- **Local Multi-Process Orchestrator**: `run-local.ps1` starts Docker PostGIS, runs database migrations, boots the FastAPI backend, compiles/starts the Next.js production server, and spawns the durable agent worker daemon; `stop-local.ps1` terminates all tracked processes cleanly.
- Targeted lint, Pylance, database ownership, policy/schema, and integration
  evidence is recorded in [`EXECUTION_LOG.md`](./EXECUTION_LOG.md) and
  [`MASTER_EXECUTION_TRACKER.md`](./MASTER_EXECUTION_TRACKER.md).
- The benchmark aggregator and deployment preflight focused tests passed
  (16 tests); the preflight CLI passed using a temporary valid config and found
  one migration head, without connecting to a database or printing secrets.
  The checked-in environment template is rejected because it retains
  placeholders for production credentials.
- Agent planning/recovery tests: **24 passed**, including checks that only
  caller-supplied values populate required slots and that proposed tool inputs
  and dependency order are validated before execution, including rejection of
  non-finite JSON numbers.
- **Durable Worker & Agent Orchestration**: Background worker atomically claims runs with `SELECT ... FOR UPDATE SKIP LOCKED` inside transactions, persists worker leases, and performs checkpoint-based crash recovery (`recover_stale_runs`, `AgentRunOrchestrator.resume`) without re-executing completed prior steps. Retries and recovery are idempotent with bounded attempts. Migration `012_agent_run_worker_leases.py` applied. Standalone durable worker daemon (`scripts/run_agent_worker.py`) executes with signal handling and is integrated into `run-local.ps1` and `stop-local.ps1`. PostgreSQL worker tests: **7/7 passed** (`backend/tests/integration/test_durable_worker.py`).
- **Google Gemini Provider & Credential Firewall**: Production Gemini integration (`google-genai` SDK, `GeminiLLMClient`, `gemini-3.1-flash-lite`), structured JSON output, safe offline deterministic fallback, and observable fallback event auditing (`LLM_FALLBACK_ACTIVATED`). Credential firewall scans environment variables, URL query parameters, and Bearer tokens. Git-tracked credential leakage contract tests: **4/4 passed** (`backend/tests/contract/test_credential_leakage.py`). Live Gemini API integration tests: **7/7 passed** (`backend/tests/integration/test_gemini_integration.py`). Unit provider tests: **12/12 passed** (`backend/tests/unit/test_llm_provider.py`).
- **Complete End-to-End Local User Journey**: Fully automated, un-mocked PostgreSQL and live Gemini integration test (`backend/tests/integration/test_complete_user_journey.py` — **3/3 passed**) verifying:
  1. Entrepreneur Registration (`POST /auth/register`)
  2. Login with persistent cookie session (`POST /auth/login`)
  3. Economic Atlas territorial indicators & quality shading (`GET /geo/in:district:120/indicators`)
  4. Scenario creation (`POST /scenarios`)
  5. Business assumptions & deterministic calculation (`POST /scenarios/{id}/calculate`)
  6. Agent planning via live Gemini (`POST /agent-runs`, `POST /agent-runs/{id}/start`)
  7. Deterministic tool execution (`calculate_break_even` yielding exact break-even units)
  8. Ledger evidence & quantity provenance chain inspection
  9. Scenario persistence (`GET /scenarios/{id}`)
  10. Multi-format Decision Dossier generation & download (JSON, CSV with injection escaping, XLSX via `openpyxl`, PDF via `pypdf`)
  11. SSE streaming telemetry (`GET /agent-runs/{id}/events/stream`)
  12. Durable worker lease recovery and step checkpoint resume (`test_worker_lease_recovery_and_checkpoint_resume`)
  13. Offline deterministic mode operation without API credentials (`test_deterministic_mode_runs_without_api_credentials`)
- **Consolidated Journey & LLM Suite**: **41 passed, 0 failed in 286.5s**.
- Benchmark aggregation now requires exact metric coverage per task and rejects
  numeric strings; direct tool schemas also reject nested NaN/Infinity values.
  The dev dataset remains six tasks with the previously recorded canonical
  hash.
- Ruff passed for the new benchmark/deployment tooling and its tests. The
  dev benchmark remains valid at six tasks with SHA-256
  `ebef2d61f04ba32c20f27086be8fbd101c604da5f4db4e7e9194239a6cda02b5`.

## Outstanding gates before acceptance

1. Reconcile official source vintages, licences, reuse conditions, and coverage;
   record the source decision and applicable attribution.
2. Obtain qualified, current, source-backed scheme parameter/mechanism review
   and per-template finance golden references. The policy lifecycle now exists,
   but no real scheme rule has passed that review; scheme calculations must not
   be presented as approved advice.
3. Confirm pilot go/no-go evidence and current vendor/hosting terms, then
   authorize any paid services and provide secrets through an approved secret
   manager (never source control).
4. Complete worker orchestration, bounded tool execution, recovery/resume,
   provider/replay integration, and the required end-to-end workflows.
5. Obtain independent human labels for validation/frozen benchmark tasks, run
   the benchmark protocol without tuning on the frozen split, and report
   measured metrics with uncertainty.
6. Deploy only after hosting authorization; then run fresh-install, migration,
   security, and public smoke acceptance against the authorized environment.
7. Review and sign the final acceptance decision after all applicable gates
   above have evidence.

The project should remain classified as an engineering prototype until these
gates are closed and independently verified.
