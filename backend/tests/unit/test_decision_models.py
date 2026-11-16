"""
Unit Tests for Decision Intelligence Models & Simulation Engine.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 4: Decision Intelligence Engine & Scenario Laboratory (Modules 8 & 9, UC-59 to UC-74).
"""

from decimal import Decimal
import json
from types import SimpleNamespace
import uuid
import pytest

from backend.arthlens.decision.engine import DecisionIntelligenceEngine
from backend.arthlens.decision.models import (
    DECISION_MODEL_REGISTRY,
    DecisionOutcome,
    evaluate_bulk_discount,
    evaluate_credit_term_extension,
    evaluate_equipment_purchase,
    evaluate_new_location_opening,
    evaluate_new_product_addition,
    evaluate_price_change,
    evaluate_staff_hiring,
    evaluate_supplier_switch,
)
from backend.arthlens.domain.business import Money


class TestDecisionModels:
    """Tests each of the 8 authoritative versioned decision models."""

    def test_model_1_new_product_addition(self):
        """Verifies contribution margin, break-even units, and payback for a new product launch."""
        inputs = {
            "product_name": "Premium Spiced Chai Premix",
            "selling_price": 250.0,
            "variable_cost": 150.0,
            "expected_monthly_volume": 400.0,
            "setup_cost": 50000.0,
            "cannibalization_rate": 0.05,
        }
        res = evaluate_new_product_addition(inputs)
        assert res.outcome == DecisionOutcome.FEASIBLE
        # Unit margin = 250 - 150 = 100
        assert res.calculations["unit_contribution_margin"] == 100.0
        # Effective volume = 400 * 0.95 = 380 units
        assert res.calculations["effective_monthly_volume"] == 380.0
        # Monthly gross contribution = 380 * 100 = 38,000
        assert res.calculations["monthly_gross_contribution"] == 38000.0
        # Payback = 50,000 / 38,000 = ~1.3 months
        assert res.calculations["payback_period_months"] <= 2.0
        assert len(res.graph_nodes) > 0

    def test_decimal_rounding_and_result_json_serialization(self):
        result = evaluate_new_product_addition({
            "selling_price": Decimal("2.005"),
            "variable_cost": Decimal("1"),
            "expected_monthly_volume": Decimal("1"),
            "setup_cost": Decimal("0.01"),
            "cannibalization_rate": Decimal("0"),
        })

        assert result.calculations["unit_contribution_margin"] == 1.01
        json.dumps(result.to_dict(), allow_nan=False)

    def test_decision_engine_derives_financial_inputs_with_decimal(self):
        class StubFinanceEngine:
            def calculate_working_capital(self, _business_id):
                return SimpleNamespace(cash_and_bank=Money(Decimal("250000.00")))

            def calculate_pnl(self, _business_id, _start_date, _end_date):
                return SimpleNamespace(operating_profit_ebitda=Money(Decimal("195000.00")))

        engine = DecisionIntelligenceEngine(decision_repo=object(), finance_engine=StubFinanceEngine())
        result = engine.evaluate_decision(
            business_id=uuid.uuid4(),
            model_id="MACHINE_OR_EQUIPMENT_PURCHASE",
            user_inputs={
                "machine_cost": Decimal("800000.01"),
                "down_payment": Decimal("160000.02"),
                "loan_interest_rate_pct": Decimal("10.5"),
                "loan_tenure_months": 36,
                "monthly_maintenance": Decimal("6000.00"),
                "current_monthly_volume": 8000,
                "capacity_monthly_volume": 12000,
                "unit_price": Decimal("40.00"),
                "unit_variable_cost": Decimal("22.00"),
            },
            save_evaluation=False,
        )

        assert result.calculations["loan_principal"] == 639999.99
        assert result.calculations["post_purchase_cash_liquidity"] == 89999.98
        json.dumps(result.to_dict(), allow_nan=False)

    def test_model_2_machine_or_equipment_flagship_8_lakh(self):
        """Verifies the handbook's flagship ₹8 Lakh machinery purchase journey with multi-alternative financing."""
        inputs = {
            "machine_name": "Commercial Rotary Bread Baking Oven",
            "machine_cost": 800000.0,
            "down_payment": 160000.0,  # 20% down
            "loan_amount": 640000.0,
            "loan_interest_rate_pct": 10.5,
            "loan_tenure_months": 36,
            "monthly_maintenance": 6000.0,
            "current_monthly_volume": 8000.0,
            "capacity_monthly_volume": 12000.0,  # +4,000 incremental loaves
            "unit_price": 40.0,
            "unit_variable_cost": 22.0,  # Margin = ₹18/loaf
            "current_cash_liquidity": 400000.0,
            "current_monthly_ebitda": 65000.0,
        }
        res = evaluate_equipment_purchase(inputs)

        # 4,000 loaves * ₹18 = ₹72,000 incremental gross profit
        assert res.calculations["incremental_monthly_gross_profit"] == 72000.0
        # Operating gain = 72,000 - 6,000 maintenance = ₹66,000
        assert res.calculations["net_monthly_operating_gain"] == 66000.0

        # EMI for ₹6.4L at 10.5% for 36 months = ~₹20,800
        emi = res.calculations["monthly_emi"]
        assert 20000.0 <= emi <= 21500.0

        # Net monthly cash flow after debt service = 66,000 - 20,800 = ~₹45,200
        net_cf = res.calculations["net_monthly_cash_flow_after_emi"]
        assert net_cf > 44000.0

        # Ending liquidity = 400k - 160k = ₹2,40,000 (well above ₹1,50,000 safety floor)
        assert res.calculations["post_purchase_cash_liquidity"] == 240000.0

        # DSCR = (65,000 + 66,000) / emi = 131,000 / ~20,800 = ~6.3x (robust)
        assert res.calculations["debt_service_coverage_ratio_dscr"] >= 5.0

        # Decision is fully feasible
        assert res.outcome == DecisionOutcome.FEASIBLE
        # Multi-alternative generation: 3 ranked options
        assert len(res.alternatives) == 3
        assert res.alternatives[0].alternative_id == "ALT_LOAN_36M"
        assert res.alternatives[1].alternative_id == "ALT_LOAN_60M"

    def test_equipment_model_requires_all_financial_inputs(self):
        result = evaluate_equipment_purchase({"machine_cost": 800000.0})

        assert result.outcome == DecisionOutcome.INSUFFICIENT_INFORMATION
        assert result.calculations == {}
        assert "down_payment" in result.inputs["missing_inputs"]
        assert "current_cash_liquidity" in result.inputs["missing_inputs"]

    def test_model_3_supplier_switch(self):
        """Verifies annual procurement savings and credit extension benefit."""
        inputs = {
            "new_supplier_name": "Surat Yarns Ltd.",
            "current_unit_price": 120.0,
            "new_unit_price": 110.0,  # ₹10 savings / kg
            "monthly_units": 2000.0,
            "current_credit_days": 15,
            "new_credit_days": 30,  # +15 days credit
            "switching_cost": 5000.0,
        }
        res = evaluate_supplier_switch(inputs)
        assert res.outcome == DecisionOutcome.FEASIBLE
        # Monthly price savings = 2,000 * 10 = ₹20,000
        assert res.calculations["monthly_price_savings"] == 20000.0
        # Working capital freed = (110 * 2000 / 30) * 15 = ₹1,10,000
        assert res.calculations["working_capital_freed_up"] == 110000.0

    def test_model_4_bulk_discount_vs_storage(self):
        """Verifies bulk procurement savings against storage and capital lockup."""
        inputs = {
            "regular_unit_price": 50.0,
            "discounted_unit_price": 42.0,  # ₹8 discount
            "order_quantity": 5000.0,
            "monthly_consumption": 1000.0,  # 5 months holding
            "monthly_storage_per_unit": 0.50,
            "annual_cost_of_capital_pct": 12.0,
        }
        res = evaluate_bulk_discount(inputs)
        assert res.outcome == DecisionOutcome.FEASIBLE
        assert res.calculations["gross_discount_savings"] == 40000.0
        assert res.calculations["net_bulk_savings"] > 25000.0

    def test_model_5_new_branch_opening(self):
        """Verifies branch expansion EBITDA and break-even revenue."""
        inputs = {
            "location_name": "Civil Lines High Street",
            "fitout_capex": 300000.0,
            "security_deposit": 100000.0,
            "monthly_rent": 25000.0,
            "monthly_staff_cost": 20000.0,
            "monthly_utilities": 5000.0,
            "expected_daily_customers": 40.0,
            "average_order_value": 300.0,
            "gross_margin_pct": 45.0,
        }
        res = evaluate_new_location_opening(inputs)
        assert res.outcome == DecisionOutcome.FEASIBLE
        # Monthly fixed overhead = 25k + 20k + 5k = ₹50,000
        assert res.calculations["monthly_fixed_overhead"] == 50000.0
        # Expected revenue = 40 * 30 * 300 = ₹3,60,000
        assert res.calculations["expected_monthly_revenue"] == 360000.0
        assert res.calculations["expected_monthly_ebitda"] > 100000.0

    def test_model_6_staff_hiring(self):
        """Verifies sales specialist hiring with break-even sales calculation."""
        inputs = {
            "role_title": "Field Sales Officer",
            "monthly_fixed_salary": 22000.0,
            "commission_pct": 3.0,
            "benefits_and_overhead": 3000.0,
            "expected_incremental_revenue": 200000.0,
            "gross_margin_pct": 30.0,
        }
        res = evaluate_staff_hiring(inputs)
        assert res.outcome == DecisionOutcome.FEASIBLE
        assert res.calculations["total_monthly_employment_cost"] == 31000.0  # 25k fixed + 6k comm
        assert res.calculations["net_monthly_contribution"] == 29000.0  # 60k gross - 31k cost

    def test_model_7_credit_term_extension(self):
        """Verifies customer credit extension balancing sales growth with default risk."""
        inputs = {
            "customer_name": "Metro Retailers",
            "current_monthly_sales": 100000.0,
            "expected_sales_increase_pct": 25.0,
            "current_terms_days": 15,
            "proposed_terms_days": 45,
            "gross_margin_pct": 25.0,
            "default_risk_pct": 1.5,
            "annual_cost_of_capital_pct": 12.0,
        }
        res = evaluate_credit_term_extension(inputs)
        assert res.outcome == DecisionOutcome.FEASIBLE
        assert res.calculations["incremental_gross_profit"] == 6250.0
        assert res.calculations["net_monthly_economic_gain"] > 2500.0

    def test_model_8_price_change_elasticity(self):
        """Verifies price increase with price elasticity of demand."""
        inputs = {
            "product_name": "Standard Brass Faucet",
            "current_price": 500.0,
            "proposed_price": 550.0,  # +10% price
            "current_monthly_volume": 600.0,
            "unit_variable_cost": 300.0,
            "price_elasticity_of_demand": -0.8,  # Inelastic: volume drops only 8%
        }
        res = evaluate_price_change(inputs)
        assert res.outcome == DecisionOutcome.FEASIBLE
        assert res.calculations["price_change_percent"] == 10.0
        assert res.calculations["projected_volume_change_percent"] == -8.0
        assert res.calculations["net_monthly_profit_difference"] > 0


class TestSimulationAndSensitivity:
    """Tests Monte Carlo PCG64 risk simulations and OAT sensitivity analysis."""

    class _FinanceStub:
        def calculate_working_capital(self, _business_id):
            return SimpleNamespace(cash_and_bank=Money.from_decimal("100000.00"))

        def calculate_pnl(self, _business_id, _start_date, _end_date):
            return SimpleNamespace(operating_profit_ebitda=Money.from_decimal("30000.00"))

    def test_monte_carlo_pcg64_reproducibility(self):
        """Verifies that running Monte Carlo with the same seed produces identical P10/P50/P90 distributions."""
        engine = DecisionIntelligenceEngine(finance_engine=self._FinanceStub())
        biz_id = uuid.uuid4()
        base_inputs = {
            "product_name": "Handmade Leather Bag",
            "selling_price": 1800.0,
            "variable_cost": 950.0,
            "expected_monthly_volume": 150.0,
            "setup_cost": 40000.0,
        }
        uncertainty = {
            "selling_price": {"std_dev_pct": 0.08},
            "expected_monthly_volume": {"std_dev_pct": 0.15},
            "variable_cost": {"std_dev_pct": 0.10},
        }

        # Run 1
        res1 = engine.run_monte_carlo_simulation(
            business_id=biz_id,
            model_id="NEW_PRODUCT_ADDITION",
            base_inputs=base_inputs,
            uncertainty_params=uncertainty,
            iterations=500,
            random_seed=12345,
        )

        # Run 2 with identical seed
        res2 = engine.run_monte_carlo_simulation(
            business_id=biz_id,
            model_id="NEW_PRODUCT_ADDITION",
            base_inputs=base_inputs,
            uncertainty_params=uncertainty,
            iterations=500,
            random_seed=12345,
        )

        # Verify exact reproducibility down to the decimal
        p50_run1 = res1["stochastic_metrics"]["monthly_gross_contribution"]["p50_median"]
        p50_run2 = res2["stochastic_metrics"]["monthly_gross_contribution"]["p50_median"]
        assert p50_run1 == p50_run2

        # P10 <= P50 <= P90 invariant
        metrics = res1["stochastic_metrics"]["monthly_gross_contribution"]
        assert metrics["p10_downside"] <= metrics["p50_median"] <= metrics["p90_upside"]
        assert res1["shortfall_risk_probability_percent"] >= 0.0

    def test_oat_sensitivity_tornado_ranking(self):
        """Verifies that OAT sensitivity correctly ranks input parameters by swing magnitude."""
        engine = DecisionIntelligenceEngine(finance_engine=self._FinanceStub())
        biz_id = uuid.uuid4()
        base_inputs = {
            "machine_name": "Hydraulic Press 50 Ton",
            "machine_cost": 600000.0,
            "down_payment": 120000.0,
            "loan_amount": 480000.0,
            "loan_interest_rate_pct": 11.0,
            "loan_tenure_months": 36,
            "monthly_maintenance": 4000.0,
            "current_monthly_volume": 5000.0,
            "capacity_monthly_volume": 8500.0,
            "unit_price": 60.0,
            "unit_variable_cost": 35.0,
            "current_cash_liquidity": 300000.0,
            "current_monthly_ebitda": 45000.0,
        }

        tornado = engine.run_sensitivity_analysis(
            business_id=biz_id,
            model_id="MACHINE_OR_EQUIPMENT_PURCHASE",
            base_inputs=base_inputs,
            target_output_metric="net_monthly_cash_flow_after_emi",
            variation_pct=0.20,
        )

        assert len(tornado) >= 3
        # Verify descending order of swing magnitude
        for i in range(len(tornado) - 1):
            assert tornado[i]["swing"] >= tornado[i + 1]["swing"]
        # Unit price and unit variable cost are top drivers of cash flow
        top_params = [p["parameter"] for p in tornado[:3]]
        assert any(p in top_params for p in ("unit_price", "unit_variable_cost", "capacity_monthly_volume"))
