# Benchmark Tasks — Development Split (`dev`)

> **Handbook Reference**: Section 12.2 (Agent Benchmark Design)  
> **Task**: P0-5  
> **Schema**: [`../../task_schema.json`](../task_schema.json)

---

## 1. Purpose of the Development Split

The `dev` split is used for active agent development, prompt engineering, heuristic tuning, and failure mode analysis. Developers and agents may inspect tasks in this directory and evaluate agent outputs against them iteratively.

## 2. Split Rules & Policies

1. **Permitted Use**:
   - Inspecting task questions, contexts, and expected outcomes.
   - Prompt iteration, plan-validator tuning, and recovery strategy development.
   - Running automated regression evaluations during development.
2. **Quality & Validation**:
   - Every task file must validate strictly against [`benchmark/task_schema.json`](../task_schema.json).
   - Task IDs in this split must be unique (convention: `BT-001` through `BT-099` or prefixed `BT-DEV-xxx`).
   - Tasks must span all three ArthLens workflow loops:
     - **Loop A**: Question to verified answer.
     - **Loop B**: Opportunity to decision.
     - **Loop C**: Scheme to financial impact.
3. **Six Required Benchmark Categories (Handbook 12.2)**:
   - `answerable`: Factual or analytical question answerable with available data.
   - `insufficient_evidence`: Data gap where the agent must report missing data rather than fabricating numbers.
   - `conflicting_sources`: Multiple sources report differing figures; agent must detect conflict and flag uncertainty.
   - `geographic_resolution_trap`: Data is available only at state/district level; query asks for block/village without registered downscaling.
   - `scheme_edge_case`: Boundary condition for scheme eligibility (e.g. investment ceiling, caste/gender criteria).
   - `injected_tool_failure`: Simulated tool error or network failure to test recovery and graceful degradation.
4. **Synthetic Data Policy (P0-5)**:
   - The initial sample tasks in `sample_tasks.json` are synthetic templates.
   - In accordance with Handbook Rule 0.2, real numeric values are not invented; gold answers are populated only from verified sources or reference calculations.
5. **Independent Labeling**:
   - Per Handbook Section 12.2, someone other than the primary task author must label or audit at least a sample of gold answers before production evaluation.
