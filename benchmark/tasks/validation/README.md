# Benchmark Tasks — Validation Split (`validation`)

> **Handbook Reference**: Section 12.2 (Agent Benchmark Design)  
> **Task**: P0-5  
> **Schema**: [`../../task_schema.json`](../task_schema.json)

---

## 1. Purpose of the Validation Split

The `validation` split is reserved for model selection, comparative ablation studies, and architectural gating decisions. It provides an unbiased checkpoint evaluation between development iterations and final frozen benchmark testing.

## 2. Split Rules & Policies

1. **Restricted Tuning Policy**:
   - **No prompt tuning or heuristic hacking on the validation set**: Prompts and gating rules must not be modified to fit individual failures observed in this split until systematic patterns are established.
   - Do not inspect individual task failures during daily prompt development; use the `dev` split for iterative development.
2. **Evaluation Systems Evaluated (Handbook 12.2)**:
   - **B1**: Single-pass LLM with tool access, no epistemic gating.
   - **B2**: Fixed analytical pipeline (no adaptivity).
   - **B3**: Full agent with verifier gates turned off (ablation).
   - **B4**: Full ArthLens agent with the epistemic ledger and verifier gates.
3. **Core Metrics Measured**:
   - **Unsupported numeric claim rate**: Share of numbers with no ledger ID or contradicting ledger class.
   - **Class-mislabel rate**: Share of claims described as a stronger class than the computed floor.
   - **Resolution-overclaim rate**: Claims at finer resolution than evidence supports without registered downscaling.
   - **Correct insufficient-evidence rate**: On unanswerable tasks, share where the agent correctly reports the gap.
   - **Eligibility accuracy**: Agreement with human-labelled truth table.
   - **Numerical correctness**: Agreement with reference calculations within tolerance.
   - **Completion & recovery**: Success under injected failures.
   - **Cost and latency**: Model calls, tool calls, latency, and USD cost per completed task.
4. **Schema Compliance**:
   - All tasks in this directory must have `"split": "validation"` and conform strictly to [`benchmark/task_schema.json`](../task_schema.json).
