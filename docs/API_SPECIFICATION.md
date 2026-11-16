# ArthLens REST API Specification

**Local base URL:** http://127.0.0.1:8000  
**Business route prefix:** /businesses  
**Authentication:** HTTP-only session cookie or Authorization: Bearer token.  
**Authorization:** Deny-by-default endpoint policy, workspace membership/role checks, and tenant-scoped service queries.

The FastAPI route definitions in backend/arthlens/api/auth.py, backend/arthlens/api/business.py, and backend/arthlens/api/admin.py are authoritative. The feature routes below reflect the current business router.

## Health and authentication

| Method | Path | Purpose |
|---|---|---|
| GET | /health, /api/v1/health | Basic service health |
| GET | /health/live | Liveness probe |
| GET | /health/ready | Database readiness probe |
| POST | /auth/register | Register an entrepreneur and establish a session |
| POST | /auth/login | Authenticate and establish a session |
| POST | /auth/logout | Revoke/clear the current session |
| POST | /auth/refresh | Refresh a session |
| GET | /auth/me | Current user profile |
| GET | /auth/ping | Authentication service ping |
| POST | /auth/password-reset/request | Request recovery |
| POST | /auth/password-reset/confirm | Confirm recovery |

## Workspaces and operations

- GET/POST /businesses: list or create workspaces; GET /businesses/portfolio returns the workspace portfolio.
- GET/PUT /businesses/{business_id}: retrieve or update a workspace.
- POST /businesses/{business_id}/archive: archive or unarchive using an is_archived body field.
- GET/POST /businesses/{business_id}/members, PATCH/DELETE /businesses/{business_id}/members/{target_user_id}: membership and role lifecycle.
- Customer and supplier records and ledgers are under /businesses/{business_id}/customers and /suppliers.
- Products, stock adjustments, balances, and movements are under /products and /inventory.
- Sales use /invoices, invoice payment/cancel routes, and /returns/sales.
- Purchases use /purchases, purchase payment routes, and /returns/purchases.
- Khata reconciliation is POST /businesses/{business_id}/khata/reconcile.
- Cash, income, expense, period close, transaction, journal, and trial-balance routes are under the corresponding /cash-position, /income, /expenses, /periods, /transactions, and /ledger paths.

## New service-backed endpoints

| Service | Endpoints | Behavior |
|---|---|---|
| inventory_cost_service | GET /businesses/{business_id}/inventory/unreconciled-costs; POST /businesses/{business_id}/inventory/reconcile-costs; GET /businesses/{business_id}/inventory/cost-reconciliation-history | Inspect unresolved movement costs, reconcile by chronological replay or manual attestation, and read durable run/event history. |
| scenario_service | POST/GET /businesses/{business_id}/scenarios; POST /businesses/{business_id}/scenarios/compare; POST/GET /businesses/{business_id}/scenarios/{scenario_id}/versions; POST/GET /businesses/{business_id}/scenarios/{scenario_id}/runs; POST /businesses/{business_id}/scenarios/{scenario_id}/runs/{run_id}/replay | Create immutable versions, compare versions, run seeded simulations, and replay a persisted run against its captured inputs. |
| goal_planning_service | POST /businesses/{business_id}/goals/{goal_id}/evaluate; POST/GET /businesses/{business_id}/goals/{goal_id}/milestones; POST/GET /businesses/{business_id}/goals/{goal_id}/plans; POST/GET /businesses/{business_id}/goals/{goal_id}/tasks; PATCH/DELETE /businesses/{business_id}/goals/{goal_id}/tasks/{task_id} | Evaluate actual-versus-planned goal progress with evidence, manage milestones and action plans, and assign/update tasks. |
| agent_action_service | POST/GET /businesses/{business_id}/agent/sessions/{session_id}/actions; POST /businesses/{business_id}/agent/sessions/{session_id}/actions/{action_id}/confirm; POST /businesses/{business_id}/agent/sessions/{session_id}/actions/{action_id}/reject; GET /businesses/{business_id}/agent/sessions/{session_id}/actions/{action_id}/download | Store validated proposals as PENDING_CONFIRMATION; only explicit confirmation executes supported goal/task/report actions. Reject and report-download endpoints complete the action lifecycle. |

## Financial and decision intelligence

- GET /businesses/{business_id}/analytics/pnl
- GET /businesses/{business_id}/analytics/cash-flow
- GET /businesses/{business_id}/analytics/working-capital
- GET /businesses/{business_id}/analytics/ageing
- GET /businesses/{business_id}/analytics/break-even
- GET /businesses/{business_id}/analytics/health-score
- POST /businesses/{business_id}/decisions/evaluate, /simulate-risk, and /sensitivity
- GET /businesses/{business_id}/decisions/history
- GET /businesses/{business_id}/decisions/{decision_id}/versions returns persisted decision lineage, causal graph, and evidence.
- POST /businesses/{business_id}/agent/investigate starts a tenant-bound investigation.
- Reports include dossier PDF, decision brief PDF, invoice PDF, ledger CSV, and customer/supplier ledger exports under /businesses/{business_id}/reports and /invoices.

## Workspace frontend routes

The Next.js workspace UI contains 18 page routes rooted at /workspaces/[id]: overview, agent, analytics, audit, constellation, customers, decisions, finance, goals, inventory, khata, members, purchases, reports, sales, scenarios, settings, and suppliers. Exact paths are listed in README.md and implemented under frontend/app/workspaces/[id].