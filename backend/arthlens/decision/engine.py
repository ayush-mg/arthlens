"""
Decision Intelligence Engine & Simulation Orchestrator.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 4: Decision Intelligence Engine & Scenario Laboratory (Modules 8 & 9, UC-59 to UC-74).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid

import numpy as np
from numpy.random import PCG64, Generator

from backend.arthlens.decision.models import (
    DECISION_MODEL_REGISTRY,
    DecisionEvaluationResult,
    DecisionOutcome,
)
from backend.arthlens.domain.business import DecisionEvaluation
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine
from backend.arthlens.infra.business_repositories import (
    PostgresDecisionEvaluationRepository,
)


class DecisionInputValidationError(ValueError):
    """Input failure with actionable, machine-readable validation details."""

    def __init__(self, missing_fields: list[str], contradictions: list[str], hard_constraint_violations: list[str]):
        self.details = {
            "missing_fields": missing_fields,
            "contradictions": contradictions,
            "hard_constraint_violations": hard_constraint_violations,
        }
        super().__init__("Decision inputs are incomplete or contradictory.")


_REQUIRED_DECISION_INPUTS: dict[str, tuple[str, ...]] = {
    "MACHINE_OR_EQUIPMENT_PURCHASE": (
        "machine_cost", "down_payment", "loan_interest_rate_pct", "loan_tenure_months",
        "monthly_maintenance", "current_monthly_volume", "capacity_monthly_volume", "unit_price", "unit_variable_cost",
    ),
    "NEW_PRODUCT_ADDITION": ("product_name", "selling_price", "variable_cost", "expected_monthly_volume", "setup_cost", "cannibalization_rate"),
    "SUPPLIER_SWITCH_OR_CREDIT_TERMS": ("new_supplier_name", "current_unit_price", "new_unit_price", "monthly_units", "current_credit_days", "new_credit_days", "switching_cost"),
    "BULK_DISCOUNT_VS_STORAGE_COST": ("regular_unit_price", "discounted_unit_price", "order_quantity", "monthly_consumption", "monthly_storage_per_unit", "annual_cost_of_capital_pct"),
    "NEW_BRANCH_OR_LOCATION_OPENING": ("location_name", "fitout_capex", "security_deposit", "monthly_rent", "monthly_staff_cost", "monthly_utilities", "expected_daily_customers", "average_order_value", "gross_margin_pct"),
    "HIRING_STAFF_OR_COMMISSION": ("role_title", "monthly_fixed_salary", "commission_pct", "benefits_and_overhead", "expected_incremental_revenue", "gross_margin_pct"),
    "CREDIT_TERM_EXTENSION_TO_CUSTOMER": ("customer_name", "current_monthly_sales", "expected_sales_increase_pct", "current_terms_days", "proposed_terms_days", "gross_margin_pct", "default_risk_pct", "annual_cost_of_capital_pct"),
    "PRICE_INCREASE_OR_DISCOUNT": ("product_name", "current_price", "proposed_price", "current_monthly_volume", "unit_variable_cost", "price_elasticity_of_demand"),
    "FINANCING_COMPARISON": ("purchase_cost", "monthly_operating_gain", "available_cash", "loan_interest_rate_pct", "loan_term_months", "lease_monthly_payment", "lease_term_months", "equity_injection", "discount_rate_pct"),
    "BUSINESS_EXPANSION": ("expansion_capex", "projected_monthly_revenue", "gross_margin_pct", "projected_monthly_opex", "available_cash", "committed_financing", "financing_mode"),
    "INVENTORY_PROCUREMENT": ("unit_cost", "order_quantity", "monthly_demand", "current_stock", "reorder_threshold", "holding_cost_per_unit_month", "stockout_cost_per_unit", "supplier_lead_time_days"),
    "CUSTOMER_CREDIT_RISK": ("customer_name", "current_receivable", "credit_limit", "requested_sale_amount", "average_monthly_sales", "gross_margin_pct", "default_risk_pct", "annual_cost_of_capital_pct", "proposed_terms_days", "overdue_days"),
    "COST_REDUCTION": ("cost_category", "current_monthly_cost", "proposed_monthly_cost", "one_time_implementation_cost", "expected_quality_cost_monthly", "evaluation_months"),
    "CASH_FLOW_PRESSURE": ("cash_balance", "monthly_cash_inflows", "monthly_cash_outflows", "receivables_due_30d", "receivables_collectible_amount", "payables_due_30d", "payables_deferral_amount", "credit_line_available", "credit_line_draw_amount", "credit_line_interest_pct", "monthly_survival_threshold"),
    "BUSINESS_VIABILITY": ("current_monthly_revenue", "variable_cost_pct", "monthly_fixed_costs", "cash_balance", "monthly_debt_service", "current_working_capital", "monthly_revenue_growth_pct", "annual_interest_rate_pct", "monthly_capex", "current_debt"),
    "LOCATION_SELECTION": ("candidates",),
}


def _input_decimal(value: Any, field: str) -> Decimal:
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite.")
    return parsed


def _money_as_decimal(value: Any) -> Decimal:
    """Read exact Money amounts, with compatibility for float-only finance adapters."""
    amount = getattr(value, "amount", None)
    if amount is None:
        raise TypeError("Financial metrics must expose an exact Money amount.")
    decimal_amount = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    if not decimal_amount.is_finite():
        raise ValueError("Financial metrics must be finite.")
    return decimal_amount


class DecisionIntelligenceEngine:
    """
    Evaluates business decisions using versioned mathematical graphs,
    enforces explicit financial constraints, runs Monte Carlo simulations (PCG64),
    computes OAT sensitivity tornado diagrams, and records immutable audit evaluations.
    """

    def __init__(
        self,
        decision_repo: Optional[PostgresDecisionEvaluationRepository] = None,
        finance_engine: Optional[FinancialIntelligenceEngine] = None,
    ):
        self.decision_repo = decision_repo or PostgresDecisionEvaluationRepository()
        self.finance_engine = finance_engine or FinancialIntelligenceEngine()

    def _enrich_financial_inputs(
        self, business_id: uuid.UUID, user_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Bind decision inputs to user supplied terms and verified ledger records."""
        enriched = {key: value for key, value in user_inputs.items() if key != "input_provenance"}
        provenance: dict[str, str] = {}

        def record_paths(value: Any, path: str) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    record_paths(nested, f"{path}.{key}" if path else str(key))
            elif isinstance(value, (list, tuple)):
                for index, nested in enumerate(value):
                    record_paths(nested, f"{path}[{index}]")
            else:
                provenance[path] = "USER_ASSUMPTION"

        for key, value in enriched.items():
            record_paths(value, key)
        if (
            "loan_amount" not in enriched
            and enriched.get("machine_cost") is not None
            and enriched.get("down_payment") is not None
        ):
            enriched["loan_amount"] = Decimal(str(enriched["machine_cost"])) - Decimal(str(enriched["down_payment"]))
            provenance["loan_amount"] = "USER_ASSUMPTION"

        working_capital = self.finance_engine.calculate_working_capital(business_id)
        enriched["current_cash_liquidity"] = _money_as_decimal(working_capital.cash_and_bank)
        provenance["current_cash_liquidity"] = "LEDGER_ACTUAL"

        pnl = self.finance_engine.calculate_pnl(business_id, date.today() - timedelta(days=90), date.today())
        enriched["current_monthly_ebitda"] = _money_as_decimal(pnl.operating_profit_ebitda) / Decimal("3")
        provenance["current_monthly_ebitda"] = "LEDGER_ACTUAL"
        enriched["input_provenance"] = provenance
        return enriched

    @staticmethod
    def _input_leaf_values(inputs: Dict[str, Any]):
        def visit(value: Any, path: str):
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key != "input_provenance":
                        yield from visit(nested, f"{path}.{key}" if path else str(key))
            elif isinstance(value, (list, tuple)):
                for index, nested in enumerate(value):
                    yield from visit(nested, f"{path}[{index}]")
            else:
                yield path, value
        for key, value in inputs.items():
            if key != "input_provenance":
                yield from visit(value, key)

    def evaluate_decision(
        self,
        business_id: uuid.UUID,
        model_id: str,
        user_inputs: Dict[str, Any],
        constraints_override: Optional[Dict[str, Any]] = None,
        save_evaluation: bool = True,
        parent_decision_id: uuid.UUID | None = None,
    ) -> DecisionEvaluationResult:
        """
        Orchestrates deterministic decision evaluation:
        1. Pre-populates baseline operational metrics from live PostgreSQL records if missing.
        2. Evaluates the versioned mathematical decision model.
        3. Evaluates all hard and soft constraints.
        4. Generates trade-off rankings across alternatives.
        5. Persists evaluation audit record to the database.
        """
        model_fn = DECISION_MODEL_REGISTRY.get(model_id)
        if not model_fn:
            raise ValueError(f"Unknown decision model: '{model_id}'. Available models: {list(DECISION_MODEL_REGISTRY.keys())}")

        required = _REQUIRED_DECISION_INPUTS.get(model_id, ())
        missing_fields = [field for field in required if user_inputs.get(field) is None or user_inputs.get(field) == ""]
        if missing_fields:
            raise DecisionInputValidationError(missing_fields, [], [])

        enriched_inputs = self._enrich_financial_inputs(business_id, user_inputs)

        contradictions: list[str] = []
        hard_violations: list[str] = []
        for field in ("annual_cost_of_capital_pct", "cost_of_capital_pct", "discount_rate_pct", "loan_interest_rate_pct"):
            if enriched_inputs.get(field) is not None and _input_decimal(enriched_inputs[field], field) < 0:
                contradictions.append(f"{field} cannot be negative.")
        for field in ("gross_margin_pct", "contribution_margin_pct", "variable_cost_pct", "default_risk_pct"):
            if enriched_inputs.get(field) is not None:
                margin = _input_decimal(enriched_inputs[field], field)
                if margin < 0 or margin > 100:
                    contradictions.append(f"{field} must be between 0 and 100 percent.")
        for field in ("loan_tenure_months", "loan_term_months"):
            if enriched_inputs.get(field) is not None and _input_decimal(enriched_inputs[field], field) <= 0:
                contradictions.append(f"{field} must be greater than zero.")
        if enriched_inputs.get("discount_rate") is not None and _input_decimal(enriched_inputs["discount_rate"], "discount_rate") <= -100:
            contradictions.append("discount_rate must be greater than -100 percent.")
        if model_id == "MACHINE_OR_EQUIPMENT_PURCHASE":
            machine_cost = _input_decimal(enriched_inputs["machine_cost"], "machine_cost")
            down_payment = _input_decimal(enriched_inputs["down_payment"], "down_payment")
            if machine_cost < 0 or down_payment < 0:
                contradictions.append("Machine cost and down payment cannot be negative.")
            if down_payment > machine_cost:
                contradictions.append("Down payment cannot exceed machine cost.")
            if _input_decimal(enriched_inputs["capacity_monthly_volume"], "capacity_monthly_volume") < _input_decimal(enriched_inputs["current_monthly_volume"], "current_monthly_volume"):
                hard_violations.append("Post-purchase capacity cannot be below current monthly volume.")
        nonnegative_fields: dict[str, tuple[str, ...]] = {
            "FINANCING_COMPARISON": ("purchase_cost", "monthly_operating_gain", "available_cash", "lease_monthly_payment", "equity_injection"),
            "BUSINESS_EXPANSION": ("expansion_capex", "projected_monthly_revenue", "projected_monthly_opex", "available_cash", "committed_financing"),
            "INVENTORY_PROCUREMENT": ("unit_cost", "order_quantity", "monthly_demand", "current_stock", "reorder_threshold", "holding_cost_per_unit_month", "stockout_cost_per_unit", "supplier_lead_time_days"),
            "CUSTOMER_CREDIT_RISK": ("current_receivable", "credit_limit", "requested_sale_amount", "average_monthly_sales", "proposed_terms_days", "overdue_days"),
            "COST_REDUCTION": ("current_monthly_cost", "proposed_monthly_cost", "one_time_implementation_cost", "expected_quality_cost_monthly", "evaluation_months"),
            "CASH_FLOW_PRESSURE": ("cash_balance", "monthly_cash_inflows", "monthly_cash_outflows", "receivables_due_30d", "receivables_collectible_amount", "payables_due_30d", "payables_deferral_amount", "credit_line_available", "credit_line_draw_amount", "monthly_survival_threshold"),
            "BUSINESS_VIABILITY": ("current_monthly_revenue", "monthly_fixed_costs", "cash_balance", "monthly_debt_service", "monthly_capex", "current_debt"),
        }
        for field in nonnegative_fields.get(model_id, ()):
            if _input_decimal(enriched_inputs[field], field) < 0:
                contradictions.append(f"{field} cannot be negative.")
        if model_id == "FINANCING_COMPARISON":
            for field in ("loan_term_months", "lease_term_months"):
                if _input_decimal(enriched_inputs[field], field) <= 0:
                    contradictions.append(f"{field} must be greater than zero.")
        if model_id == "BUSINESS_EXPANSION" and financing_mode == "OWN_CAPITAL":
            required_capex = _input_decimal(enriched_inputs["expansion_capex"], "expansion_capex")
            stated_funding = _input_decimal(enriched_inputs["available_cash"], "available_cash") + _input_decimal(enriched_inputs["committed_financing"], "committed_financing")
            if required_capex > stated_funding:
                hard_violations.append("Expansion capex exceeds stated available cash plus committed financing.")
        if model_id == "CASH_FLOW_PRESSURE":
            if _input_decimal(enriched_inputs["receivables_collectible_amount"], "receivables_collectible_amount") > _input_decimal(enriched_inputs["receivables_due_30d"], "receivables_due_30d"):
                hard_violations.append("Accelerated collections exceed receivables due within 30 days.")
            if _input_decimal(enriched_inputs["payables_deferral_amount"], "payables_deferral_amount") > _input_decimal(enriched_inputs["payables_due_30d"], "payables_due_30d"):
                hard_violations.append("Proposed payable deferral exceeds payables due within 30 days.")
            if _input_decimal(enriched_inputs["credit_line_draw_amount"], "credit_line_draw_amount") > _input_decimal(enriched_inputs["credit_line_available"], "credit_line_available"):
                hard_violations.append("Requested credit-line draw exceeds available facility.")
            if _input_decimal(enriched_inputs["monthly_survival_threshold"], "monthly_survival_threshold") <= 0:
                contradictions.append("monthly_survival_threshold must be greater than zero.")
        if model_id == "BUSINESS_VIABILITY" and _input_decimal(enriched_inputs["monthly_revenue_growth_pct"], "monthly_revenue_growth_pct") <= -100:
            contradictions.append("monthly_revenue_growth_pct must be greater than -100 percent.")
        if model_id == "LOCATION_SELECTION":
            candidates = enriched_inputs["candidates"]
            if not isinstance(candidates, list) or not candidates:
                missing_fields.append("candidates")
            else:
                candidate_required = ("location_name", "fitout_capex", "monthly_rent", "monthly_staff_cost", "catchment_monthly_demand", "conversion_rate_pct", "average_order_value", "gross_margin_pct", "cannibalization_pct")
                for index, candidate in enumerate(candidates):
                    if not isinstance(candidate, dict):
                        contradictions.append(f"candidates[{index}] must be an object.")
                        continue
                    for field in candidate_required:
                        if candidate.get(field) is None or candidate.get(field) == "":
                            missing_fields.append(f"candidates[{index}].{field}")
                    for field in ("fitout_capex", "monthly_rent", "monthly_staff_cost", "catchment_monthly_demand", "average_order_value"):
                        if candidate.get(field) is not None and _input_decimal(candidate[field], f"candidates[{index}].{field}") < 0:
                            contradictions.append(f"candidates[{index}].{field} cannot be negative.")
                    for field in ("conversion_rate_pct", "gross_margin_pct", "cannibalization_pct"):
                        if candidate.get(field) is not None and not Decimal("0") <= _input_decimal(candidate[field], f"candidates[{index}].{field}") <= Decimal("100"):
                            contradictions.append(f"candidates[{index}].{field} must be between 0 and 100 percent.")
        financing_mode = str(enriched_inputs.get("financing_mode", "")).upper()
        capex = enriched_inputs.get("capex", enriched_inputs.get("fitout_capex", enriched_inputs.get("expansion_capex")))
        if financing_mode == "OWN_CAPITAL" and capex is not None:
            available_cash = _input_decimal(enriched_inputs["current_cash_liquidity"], "current_cash_liquidity")
            if _input_decimal(capex, "capex") > available_cash:
                hard_violations.append("Own-capital investment exceeds verified available cash.")
        if missing_fields or contradictions or hard_violations:
            raise DecisionInputValidationError(missing_fields, contradictions, hard_violations)

        # Execute decision model evaluation
        result = model_fn(enriched_inputs, constraints_override)
        # Keep the public result contract JSON-number based while calculations use Decimal.
        result = replace(result, inputs=result.to_dict()["inputs"])

        # Persist audit record
        if save_evaluation:
            serialized_result = result.to_dict()
            eval_record = DecisionEvaluation(
                id=uuid.uuid4(),
                business_id=business_id,
                model_id=result.model_id,
                model_version=result.model_version,
                objective=result.objective,
                inputs_snapshot=serialized_result["inputs"],
                constraints_evaluated=[c.to_dict() for c in result.constraints],
                calculations_performed=serialized_result["calculations"],
                alternatives_evaluated=[a.to_dict() for a in result.alternatives],
                outcome=result.outcome,
                explanation=result.summary_explanation,
                parent_decision_id=parent_decision_id,
                causal_graph=serialized_result.get("graph", {}),
                evidence_items=[
                    {
                        "source_type": source,
                        "record_id": f"{business_id}:decision-input:{path}",
                        "label": path.replace("_", " ").replace(".", " / "),
                        "metric_value": str(value),
                        "timestamp": date.today().isoformat(),
                    }
                    for path, value in self._input_leaf_values(enriched_inputs)
                    if (source := enriched_inputs.get("input_provenance", {}).get(path))
                ],
            )
            saved = self.decision_repo.save(eval_record)
            result = replace(
                result,
                evaluation_id=str(saved.id),
                version_number=saved.version_number,
                parent_decision_id=str(parent_decision_id) if parent_decision_id else None,
            )

        return result

    def run_monte_carlo_simulation(
        self,
        business_id: uuid.UUID,
        model_id: str,
        base_inputs: Dict[str, Any],
        uncertainty_params: Dict[str, Dict[str, float]],  # param_name -> {"std_dev_pct": float, "distribution": "normal"|"triangular"}
        iterations: int = 1000,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Runs reproducible Monte Carlo risk simulation using NumPy PCG64.
        Returns P10 (downside risk), P50 (median expectation), P90 (upside potential),
        and probability of failing critical constraints.
        """
        model_fn = DECISION_MODEL_REGISTRY.get(model_id)
        if not model_fn:
            raise ValueError(f"Unknown decision model: '{model_id}'")

        # Initialize PCG64 random generator
        bit_generator = PCG64(random_seed)
        rng = Generator(bit_generator)

        enriched_inputs = self._enrich_financial_inputs(business_id, base_inputs)
        protected_ledger_inputs = {"current_cash_liquidity", "current_monthly_ebitda"}
        if not uncertainty_params:
            uncertainty_params = {}
            for k, v in enriched_inputs.items():
                if (
                    k in protected_ledger_inputs
                    or k in {"input_provenance", "product_name", "machine_name", "location_name", "role_title", "new_supplier_name", "customer_name", "financing_mode"}
                    or "month" in k
                    or "days" in k
                    or "tenure" in k
                    or "term" in k
                ):
                    continue
                try:
                    num_val = float(v)
                    if num_val > 0:
                        uncertainty_params[k] = {"std_dev_pct": 0.10, "distribution": "normal"}
                except (TypeError, ValueError):
                    pass

        for param in uncertainty_params:
            if param in protected_ledger_inputs:
                raise ValueError(f"Cannot simulate uncertainty for verified ledger input '{param}'.")
            if param not in enriched_inputs:
                raise ValueError(f"Unknown uncertainty input '{param}' for model '{model_id}'.")

        # Determine target output metrics to track from the authoritative baseline.
        baseline_res = model_fn(enriched_inputs, None)
        if baseline_res.outcome == DecisionOutcome.INSUFFICIENT_INFORMATION:
            missing = baseline_res.inputs.get("missing_inputs", [])
            raise ValueError("Cannot simulate without required inputs: " + ", ".join(missing))
        tracked_metrics = list(baseline_res.calculations.keys())
        sim_data: Dict[str, List[float]] = {k: [] for k in tracked_metrics}
        failures = 0

        for _ in range(iterations):
            sampled_inputs = dict(enriched_inputs)
            for param, spec in uncertainty_params.items():
                base_val = float(enriched_inputs[param])
                std_pct = spec.get("std_dev_pct", 0.10)  # default 10% std dev
                # Sample using normal distribution truncated at positive
                sampled_val = max(0.01, rng.normal(base_val, base_val * std_pct))
                sampled_inputs[param] = sampled_val

            eval_res = model_fn(sampled_inputs, None)
            if eval_res.outcome == DecisionOutcome.NOT_FEASIBLE:
                failures += 1

            for k in tracked_metrics:
                sim_data[k].append(float(eval_res.calculations.get(k, 0.0)))

        # Compute quantiles P10, P50, P90, Mean, and StdDev
        metrics_summary = {}
        for k, vals in sim_data.items():
            arr = np.array(vals)
            metrics_summary[k] = {
                "mean": round(float(np.mean(arr)), 2),
                "std_dev": round(float(np.std(arr)), 2),
                "p10_downside": round(float(np.percentile(arr, 10)), 2),
                "p50_median": round(float(np.percentile(arr, 50)), 2),
                "p90_upside": round(float(np.percentile(arr, 90)), 2),
            }

        shortfall_risk_pct = round((failures / iterations) * 100.0, 2)

        # Identify primary stochastic metric to power top-level summary cards
        primary_candidates = [
            "net_monthly_cash_flow_after_emi",
            "monthly_gross_contribution",
            "net_monthly_profit_difference",
            "annual_net_benefit",
            "net_annual_cost_savings",
            "monthly_net_benefit",
            "total_monthly_ebitda",
            "payback_period_months",
            "loan_total_cost",
            "net_monthly_gain",
        ]
        primary_metric_name = tracked_metrics[0] if tracked_metrics else "primary_metric"
        for cand in primary_candidates:
            if cand in metrics_summary:
                primary_metric_name = cand
                break
        primary_metric = metrics_summary.get(primary_metric_name, {})
        p10_val = primary_metric.get("p10_downside", 0.0)
        p50_val = primary_metric.get("p50_median", 0.0)
        p90_val = primary_metric.get("p90_upside", 0.0)

        confidence_verdict = (
            "HIGH CONFIDENCE"
            if shortfall_risk_pct < 5.0
            else ("MODERATE" if shortfall_risk_pct < 20.0 else "VOLATILE DOWNSIDE")
        )

        return {
            "model_id": model_id,
            "iterations": iterations,
            "iterations_run": iterations,
            "random_seed": random_seed,
            "primary_metric_name": primary_metric_name,
            "p10_worst_case_npv": p10_val,
            "p50_median_npv": p50_val,
            "p90_best_case_npv": p90_val,
            "probability_of_negative_npv_pct": shortfall_risk_pct,
            "shortfall_risk_probability_percent": shortfall_risk_pct,
            "confidence_verdict": confidence_verdict,
            "baseline_calculations": baseline_res.calculations,
            "stochastic_metrics": metrics_summary,
        }

    def run_sensitivity_analysis(
        self,
        business_id: uuid.UUID,
        model_id: str,
        base_inputs: Dict[str, Any],
        target_output_metric: str,
        parameters_to_vary: Optional[List[str]] = None,
        variation_pct: float = 0.20,  # +/- 20%
    ) -> List[Dict[str, Any]]:
        """
        Executes deterministic One-at-a-Time (OAT) sensitivity analysis.
        Generates ranked parameter sensitivities for Tornado chart rendering.
        """
        model_fn = DECISION_MODEL_REGISTRY.get(model_id)
        if not model_fn:
            raise ValueError(f"Unknown decision model: '{model_id}'")

        enriched_inputs = self._enrich_financial_inputs(business_id, base_inputs)
        baseline_res = model_fn(enriched_inputs, None)
        if baseline_res.outcome == DecisionOutcome.INSUFFICIENT_INFORMATION:
            missing = baseline_res.inputs.get("missing_inputs", [])
            raise ValueError("Cannot analyze sensitivity without required inputs: " + ", ".join(missing))
        if target_output_metric not in baseline_res.calculations:
            primary_candidates = [
                "net_monthly_cash_flow_after_emi",
                "monthly_gross_contribution",
                "net_monthly_profit_difference",
                "annual_net_benefit",
                "monthly_net_benefit",
                "total_monthly_ebitda",
                "payback_period_months",
                "loan_total_cost",
                "net_monthly_gain",
            ]
            target_output_metric = next(
                (c for c in primary_candidates if c in baseline_res.calculations),
                next(iter(baseline_res.calculations.keys()), target_output_metric),
            )
        base_output = float(baseline_res.calculations.get(target_output_metric, 0.0))

        def is_numeric_candidate(k: str, val: Any) -> bool:
            if (
                k in {"current_cash_liquidity", "current_monthly_ebitda", "input_provenance"}
                or "month" in k
                or "days" in k
                or "tenure" in k
                or "term" in k
            ):
                return False
            try:
                n = float(val)
                return n > 0
            except (TypeError, ValueError):
                return False

        vary_params = parameters_to_vary or [
            k for k, v in enriched_inputs.items()
            if is_numeric_candidate(k, v)
        ]
        protected_ledger_inputs = {"current_cash_liquidity", "current_monthly_ebitda"}
        if any(param in protected_ledger_inputs for param in vary_params):
            raise ValueError("Sensitivity analysis cannot vary verified ledger inputs.")

        tornado_points = []
        for param in vary_params:
            if param not in enriched_inputs:
                raise ValueError(f"Unknown sensitivity input '{param}' for model '{model_id}'.")
            try:
                base_val = float(enriched_inputs[param])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Non-numeric sensitivity input '{param}' for model '{model_id}'.") from exc
            low_val = base_val * (1.0 - variation_pct)
            high_val = base_val * (1.0 + variation_pct)

            # Low evaluation
            low_inputs = dict(enriched_inputs, **{param: low_val})
            low_res = model_fn(low_inputs, None)
            low_output = float(low_res.calculations.get(target_output_metric, 0.0))

            # High evaluation
            high_inputs = dict(enriched_inputs, **{param: high_val})
            high_res = model_fn(high_inputs, None)
            high_output = float(high_res.calculations.get(target_output_metric, 0.0))

            swing = abs(high_output - low_output)
            tornado_points.append({
                "parameter": param,
                "base_value": base_val,
                "low_input": round(low_val, 2),
                "high_input": round(high_val, 2),
                "low_output": round(low_output, 2),
                "high_output": round(high_output, 2),
                "delta_low": round(low_output - base_output, 2),
                "delta_high": round(high_output - base_output, 2),
                "swing": round(swing, 2),
            })

        # Rank by swing descending (Tornado chart order)
        tornado_points.sort(key=lambda x: x["swing"], reverse=True)
        return tornado_points

    def list_history(self, business_id: uuid.UUID) -> List[Dict[str, Any]]:
        evals = self.decision_repo.list_by_business(business_id)
        return [
            {
                "id": str(e.id),
                "business_id": str(e.business_id),
                "model_id": e.model_id,
                "model_version": e.model_version,
                "objective": e.objective,
                "outcome": e.outcome.value,
                "explanation": e.explanation,
                "version_number": e.version_number,
                "parent_decision_id": str(e.parent_decision_id) if e.parent_decision_id else None,
                "causal_graph": e.causal_graph,
                "evidence_items": e.evidence_items,
                "created_at": e.created_at.isoformat(),
            }
            for e in evals
        ]

    def list_versions(self, business_id: uuid.UUID, decision_id: uuid.UUID) -> List[Dict[str, Any]]:
        versions = self.decision_repo.list_versions(business_id, decision_id)
        return [
            {
                "id": str(item.id),
                "business_id": str(item.business_id),
                "model_id": item.model_id,
                "model_version": item.model_version,
                "version_number": item.version_number,
                "parent_decision_id": str(item.parent_decision_id) if item.parent_decision_id else None,
                "objective": item.objective,
                "inputs": item.inputs_snapshot,
                "calculations": item.calculations_performed,
                "constraints": item.constraints_evaluated,
                "alternatives": item.alternatives_evaluated,
                "outcome": item.outcome.value,
                "explanation": item.explanation,
                "causal_graph": item.causal_graph,
                "evidence_items": item.evidence_items,
                "created_at": item.created_at.isoformat(),
            }
            for item in versions
        ]
