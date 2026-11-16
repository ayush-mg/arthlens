# Test Plan and Observed Results

**Repository:** C:\arthlens  
**Review date:** 12 November 2026  
**Scope:** Local backend, Vitest, Playwright, migration, and smoke verification. Counts below are observed results, not CI claims.

## Latest passing runs

| Gate | Command/configuration | Latest result |
|---|---|---|
| Backend unit, contract, integration, agent-eval, and E2E directories | Set LLM_PROVIDER=deterministic, then run .venv/Scripts/python.exe -m pytest backend/tests/unit backend/tests/contract backend/tests/integration backend/tests/agent_eval backend/tests/e2e -q --tb=short | PASS — 291 passed; exit code 0. backend/.pytest_cache/v/cache/lastfailed was {} after this run. |
| Frontend Vitest | From frontend, npm test -- --run | PASS — 4 files and 23 tests passed. |
| Browser E2E | Start local API and Next.js frontend; from frontend, npx playwright test with the external-server config enabled | PASS — 5 tests passed across authentication/password reset, IDOR, workspace roles/archive, business operations, and intelligence/scenario/goal/agent journeys. |
| Deployment smoke | Start the API and run python deployment/smoke/run_smoke_checks.py with a registered local operator | PASS — 7 checks: liveness, readiness, login, workspace create, financial snapshot, PDF export, workspace archive. |
| Migration schema and upgrade path | Included in the backend integration suite; backend/tests/integration/test_migrations.py | PASS in the 291-test run. Checks revisions 020–025 incrementally, declared tables/columns, selected constraints, and the Alembic revision after each upgrade. |
| TypeScript and Next.js build | Previous local frontend verification | PASS — TypeScript check and production build completed. No test count applies. |

## Provider configuration affects backend agent tests

The repository root .env sets LLM_PROVIDER=gemini. A backend run inheriting that value produced 288 passes and 3 agent-intent assertion failures: two in test_agent_and_reports_api.py and one in test_flagship_demonstration_journey.py expected EQUIPMENT_PURCHASE_EVALUATION but received the original prompt as intent. The full 291-pass result was obtained by explicitly setting LLM_PROVIDER=deterministic. Use that override for repeatable local automated tests; do not interpret the Gemini-configured run as green.

## Migration path covered

The migration integration test starts the isolated schema at 019_purchase_returns and upgrades in sequence through 020_inventory_cost_reconciliation, 021_business_scenario_versions, 022_goal_planning_records, 023_decision_version_graphs, 024_agent_action_confirmation, and 025_workspace_role_matrix. For each revision it checks expected columns/tables and the current alembic_version value; it also verifies constraints including reconciliation status, decision version, action type/status, and the six-role membership matrix.

The passing test run is against the configured local PostgreSQL/PostGIS test database. It does not validate a production backup/restore procedure or a production deployment’s historical data.

## Playwright coverage boundary

The current five browser tests cover authentication and password recovery, cross-tenant IDOR, workspace role changes and archival, purchase/sales operations and returns, and a financial intelligence journey through decisions, scenario replay, goal evaluation, agent confirmation, and report export. The frontend has 18 workspace page routes; a five-test browser suite does not imply each route has independent UI coverage.

## Acceptance work not covered by these counts

- Verify schema upgrade and rollback procedures against the actual supported production predecessor and a restorable backup.
- Expand direct browser assertions for each workspace route and accessibility behavior.
- Review numeric API boundary precision and document the intended rounding contract.
- Run deployment checks against a production-shaped environment and record CI results separately.

Previous values of 234 backend tests, 19 Vitest tests, and 2 Playwright tests are superseded by the counts above.