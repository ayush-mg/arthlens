# Benchmark Tasks — Frozen Test Split (`frozen_test`)

> **Handbook Reference**: Section 12.2 (Agent Benchmark Design)  
> **Task**: P0-5  
> **Schema**: [`../../task_schema.json`](../task_schema.json)

---

## 1. Purpose of the Frozen Test Split

The `frozen_test` split is the final, held-out evaluation set for ArthLens. It provides the authoritative empirical basis for all reported benchmark metrics, placement/portfolio presentations, and academic evaluations.

## 2. Non-Negotiable Split Rules (Handbook 12.2)

1. **NEVER TUNE ON FROZEN TEST**:
   - **Absolute prohibition**: Never tune system prompts, user prompts, few-shot examples, recovery rules, or verifier gating thresholds on the `frozen_test` split.
   - Any prompt or algorithm change prompted by a failure on this set invalidates the frozen status of the benchmark.
2. **Held-Out Status**:
   - The tasks in this split must remain unexamined during routine agent development.
   - Evaluation on `frozen_test` is run only at major milestone checkpoints (e.g. end of Phase 4 and Phase 7).
3. **Independent Labeling & Quality Assurance**:
   - Per Handbook Section 12.2: *"Have someone other than the task author label at least a sample."*
   - All gold answers must be independently verified against official government gazettes, RBI reports, or formal ground-truth tables before inclusion.
4. **Statistical Reporting**:
   - Per Handbook Section 12.2, all benchmark results on `frozen_test` must report bootstrap confidence intervals.
   - With small sample sizes ($N \approx 60\text{--}100$), avoid asserting claims of statistical significance on small differences.
   - If B2 (fixed analytical pipeline) matches B4 (full agent) at lower cost, report that honestly.
5. **Schema Compliance**:
   - All tasks in this directory must have `"split": "frozen_test"` and conform strictly to [`benchmark/task_schema.json`](../task_schema.json).
