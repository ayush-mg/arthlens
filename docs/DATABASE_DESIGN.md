# ArthLens Database Design

**Database:** PostgreSQL with PostGIS  
**Migration tool:** Alembic  
**Current revision:** 025_workspace_role_matrix  
**Migration graph:** One linear head; 025 descends from 024, continuing back through 020 to 019_purchase_returns.

Earlier migrations 001–019 provide platform identity, tenant, ledger, inventory-cost-basis, and purchase-return foundations. The current revision series adds the schema below.

## Revisions 020–025

| Revision | Upgrade path and schema changes |
|---|---|
| 020_inventory_cost_reconciliation | Follows 019_purchase_returns. Widens alembic_version.version_num from VARCHAR(32) to VARCHAR(64). Adds purchases.return_credit_amount NUMERIC(14,2) with a nonnegative check. Adds inventory_movements.cost_reconciliation_status, source_purchase_item_id, reconciled_at, reconciled_by_user_id, and reconciliation_note; status is constrained to VERIFIED, UNRECONCILED, ESTIMATED, or CONFLICTING. Adds inventory_cost_reconciliations and inventory_cost_reconciliation_events for tenant-scoped runs and per-movement evidence. Backfills purchase movement costs and only unambiguous purchase-return links; unsupported historical cost remains UNRECONCILED. |
| 021_business_scenario_versions | Follows 020. Adds business_scenarios, business_scenario_versions, and business_simulation_runs. Scenario versions persist assumptions and a baseline snapshot hash. Runs persist the selected scenario version, integer-valued NUMERIC seed, iteration count, distributions, baseline hash, model version, and result. Constraints bound seeds to unsigned 64-bit values and iterations to 1–100000. |
| 022_goal_planning_records | Follows 021. Adds goal_milestones, goal_action_plans, goal_action_tasks, and goal_progress_snapshots. Records include goal/business ownership, milestone targets, plan/task status, task assignment/priority/due date/expected financial impact, and planned-versus-actual/deviation snapshots with JSONB explanation and evidence. |
| 023_decision_version_graphs | Follows 022. Adds decision_evaluations.version_number, parent_decision_id (self-reference, SET NULL on parent deletion), causal_graph JSONB, and evidence_items JSONB. Adds a positive-version check and parent lookup index. |
| 024_agent_action_confirmation | Follows 023. Adds agent_proposed_actions with business/session/action identity, normalized JSONB payload, status, proposer and confirmer IDs, result JSONB, and timestamps. Checks limit status to PENDING_CONFIRMATION, CONFIRMED, or REJECTED and action type to CREATE_GOAL, CREATE_TASK, or GENERATE_REPORT. |
| 025_workspace_role_matrix | Follows 024. Expands the business_memberships.role check constraint to OWNER, ADMIN, MANAGER, ACCOUNTANT, ANALYST, and VIEWER. |

### Added table columns

- inventory_cost_reconciliations: id, business_id, mode, status, created_by, summary, created_at.
- inventory_cost_reconciliation_events: id, reconciliation_id, movement_id, product_id, classification, prior_cost_basis, resolved_cost_basis, source_evidence, resolution_note, created_at.
- business_scenarios: id, business_id, created_by_user_id, name, description, current_version, created_at, updated_at.
- business_scenario_versions: id, scenario_id, version_number, assumptions, baseline_snapshot_hash, created_by_user_id, created_at.
- business_simulation_runs: id, business_id, scenario_version_id, random_seed, iterations, distribution_config, baseline_snapshot_hash, model_version, result, created_by_user_id, created_at.
- goal_milestones: id, business_id, goal_id, title, target_date, target_value, created_by_user_id, created_at.
- goal_action_plans: id, business_id, goal_id, title, description, status, created_by_user_id, created_at.
- goal_action_tasks: id, business_id, goal_id, plan_id, title, description, assigned_member_id, priority, status, due_date, expected_financial_impact, created_by_user_id, created_at, updated_at.
- goal_progress_snapshots: id, business_id, goal_id, as_of_date, planned_value, actual_value, deviation_value, status, explanation, evidence_items, created_by_user_id, created_at.
- agent_proposed_actions: id, business_id, session_id, action_type, payload, status, created_by_user_id, confirmed_by_user_id, result, created_at, updated_at.

Revisions 020 and 023 also add columns to existing tables as described in the revision table. Revision 025 changes the membership role constraint without adding a table or column.

## Upgrade and downgrade behavior

The supported forward sequence is 019_purchase_returns → 020_inventory_cost_reconciliation → 021_business_scenario_versions → 022_goal_planning_records → 023_decision_version_graphs → 024_agent_action_confirmation → 025_workspace_role_matrix. The configured head is 025_workspace_role_matrix.

backend/tests/integration/test_migrations.py verifies the 020–025 sequence incrementally: it returns the isolated test schema to 019, upgrades to each revision in order, checks that revision’s tables and columns and selected constraints, and checks the recorded Alembic revision. It also checks role constraint values. Its broader migration tests verify fresh upgrade and downgrade/re-upgrade behavior. These tests do not establish production backup/restore or deployment-database compatibility.

Revision 025 downgrade remaps ADMIN to MANAGER and ANALYST to VIEWER before restoring the older check constraint; that downgrade is intentionally not role-preserving.

## Data and tenant relationships

- Reconciliation runs belong to a business and user; reconciliation events belong to a run, movement, and product.
- Scenarios belong to a business; versions belong to a scenario; simulation runs reference the business and immutable scenario version.
- Milestones, action plans, tasks, and progress snapshots are scoped by business and goal; tasks reference their plan.
- Decision versions form parent/child lineage through decision_evaluations.parent_decision_id.
- Proposed agent actions are scoped to the business and agent session. Confirmation records the confirming user and action result.

The ORM models and Alembic revisions are authoritative for full foreign-key, index, and nullability details. The migration test’s MIGRATION_SCHEMA mapping is the executable checklist for columns introduced in 020–025.