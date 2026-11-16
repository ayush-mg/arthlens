# ArthLens Engineering Handover

**Review date:** 12 November 2026  
**Engineering status:** Active implementation with local passing verification; production readiness is not established.

## Current implementation state

The business platform is implemented around tenant-scoped FastAPI routes and services, PostgreSQL persistence, and a Next.js workspace UI. Alembic has a single head at 025_workspace_role_matrix. Revisions 020–025 add inventory cost reconciliation, scenario versioning and simulation replay, goal planning records, decision version graphs, confirmation-gated agent actions, and the expanded workspace role matrix.

### Application services

- backend/arthlens/services/inventory_cost_service.py inspects unresolved inventory costs, performs historical reconciliation using supported replay or attestation modes, and records reconciliation runs/events.
- backend/arthlens/services/scenario_service.py stores immutable scenario versions and snapshot hashes, runs seeded Monte Carlo simulations, compares versions, and verifies replay results.
- backend/arthlens/services/goal_planning_service.py manages milestones, plans and tasks; evaluates actual against planned progress using evidence snapshots; and analyzes goal deviation.
- backend/arthlens/services/agent_action_service.py normalizes supported action payloads, binds proposals to a workspace and agent session, keeps new proposals pending, and performs writes only after explicit confirmation. Rejection and report download are separately authorized operations.

The API specification documents the associated endpoint families and tenant/RBAC expectations. Decision lineage is persisted on decision_evaluations through version_number, parent_decision_id, causal_graph, and evidence_items.

## Database upgrade path

The forward path is linear:

019_purchase_returns → 020_inventory_cost_reconciliation → 021_business_scenario_versions → 022_goal_planning_records → 023_decision_version_graphs → 024_agent_action_confirmation → 025_workspace_role_matrix

Revision 020 widens Alembic's version_num storage for the longer revision IDs, adds return-credit and inventory reconciliation fields, and creates reconciliation history tables. Revisions 021 and 022 create scenario/version/run and goal milestone/plan/task/progress tables. Revision 023 adds decision lineage fields. Revision 024 adds agent_proposed_actions and status/action checks. Revision 025 allows OWNER, ADMIN, MANAGER, ACCOUNTANT, ANALYST, and VIEWER membership roles. Downgrading 025 maps ADMIN to MANAGER and ANALYST to VIEWER, so those role distinctions are not recoverable from the downgrade.

The migration integration test checks the revisions one at a time from 019 through 025, including each revision's declared tables/columns and selected constraints. That is local schema-path evidence; it is not a production backup/restore or rollout rehearsal.

## Frontend workspace route inventory

There are 18 page routes under frontend/app/workspaces/[id]:

- /workspaces/[id]
- /workspaces/[id]/agent
- /workspaces/[id]/analytics
- /workspaces/[id]/audit
- /workspaces/[id]/constellation
- /workspaces/[id]/customers
- /workspaces/[id]/decisions
- /workspaces/[id]/finance
- /workspaces/[id]/goals
- /workspaces/[id]/inventory
- /workspaces/[id]/khata
- /workspaces/[id]/members
- /workspaces/[id]/purchases
- /workspaces/[id]/reports
- /workspaces/[id]/sales
- /workspaces/[id]/scenarios
- /workspaces/[id]/settings
- /workspaces/[id]/suppliers

The matching route inventory and short descriptions are in README.md.

## Latest local verification

| Suite | Latest passing result |
|---|---|
| Backend unit, contract, integration, agent-eval, and E2E directories | 291 passed with LLM_PROVIDER=deterministic; lastfailed cache {} |
| Vitest | 23 passed in 4 files |
| Playwright | 5 passed |
| Deployment smoke | 7 checks passed |

The backend count requires a deterministic test-provider override. The root .env requests Gemini; without the override, a recorded run had 288 passes and three agent-intent failures where tests expected a normalized equipment-purchase intent but received the prompt text. This configuration-sensitive result is detailed in TEST_PLAN_AND_RESULTS.md. These are local test results, not CI results.

## Operational and release follow-up

1. Use LLM_PROVIDER=deterministic for repeatable backend tests; use Gemini plus a valid secret only for configured integration/runtime checks.
2. Verify migration rollout, backup, and restore against the actual supported production predecessor before release.
3. Keep the revision 025 downgrade role remapping in the rollout plan; it is not lossless.
4. Review Decimal-to-JSON numeric behavior at API boundaries and confirm the product's rounding contract.
5. Treat the 18-route inventory as route existence documentation; the five Playwright tests do not independently exercise all pages.
6. Record a hosted CI run and production-shaped deployment check before asserting release readiness.