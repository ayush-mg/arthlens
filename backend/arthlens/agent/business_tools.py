"""
Deterministic business tool registry for the agentic operating system.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 5: Agentic Gemini AI Layer (Strict Dispatch, Zero-Hallucination Execution).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional
import uuid

from backend.arthlens.decision.engine import DecisionIntelligenceEngine
from backend.arthlens.domain.business import BusinessRole
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine
from backend.arthlens.services.business_service import BusinessService


class BusinessToolRegistry:
    """
    Registry of deterministic tools callable by Gemini AI or automated orchestrators.
    Guarantees that arithmetic and financial calculations are executed by verified Python functions,
    never by LLM token generation.
    """

    def __init__(
        self,
        business_service: Optional[BusinessService] = None,
        finance_engine: Optional[FinancialIntelligenceEngine] = None,
        decision_engine: Optional[DecisionIntelligenceEngine] = None,
        inventory_cost_service: Any = None,
        scenario_service: Any = None,
        goal_planning_service: Any = None,
        agent_action_service: Any = None,
    ):
        self.business_service = business_service or BusinessService()
        self.finance_engine = finance_engine or FinancialIntelligenceEngine()
        self.decision_engine = decision_engine or DecisionIntelligenceEngine()
        self.inventory_cost_service = inventory_cost_service
        self.scenario_service = scenario_service
        self.goal_planning_service = goal_planning_service
        self.agent_action_service = agent_action_service
        self._tools: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._tool_schemas: List[Dict[str, Any]] = []
        self._register_all_tools()

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns Gemini Function Calling declarations for all registered tools."""
        return self._tool_schemas

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        trusted_session_id: uuid.UUID | None = None,
    ) -> Dict[str, Any]:
        """Dispatches tool execution to the deterministic handler with strict schema & tenant verification."""
        if tool_name not in self._tools:
            return {
                "error": f"Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}",
                "status": "FAILED",
            }

        # Strict argument validation against registered schema
        schema = next((s for s in self._tool_schemas if s["name"] == tool_name), None)
        if schema:
            allowed = set(schema.get("parameters", {}).get("properties", {}).keys())
            allowed.update(["business_id", "user_id"])
            unsupported = [k for k in arguments.keys() if k not in allowed]
            if unsupported:
                return {
                    "error": f"Tool '{tool_name}' rejected unsupported arguments: {unsupported}",
                    "status": "FAILED",
                }

        try:
            handler_arguments = dict(arguments)
            # Agent actions are always tied to the session established by the
            # authenticated runtime. A model supplied session identifier is
            # never accepted through the public Gemini schema.
            if tool_name == "propose_agent_action" and trusted_session_id is not None:
                handler_arguments["_trusted_session_id"] = str(trusted_session_id)
            return self._tools[tool_name](handler_arguments)
        except Exception as e:
            return {
                "error": str(e),
                "status": "ERROR",
                "tool": tool_name,
            }

    # ==========================================================================
    # Tool Implementations
    # ==========================================================================

    def _register(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._tools[name] = handler
        self._tool_schemas.append({
            "name": name,
            "description": description,
            "parameters": parameters,
        })

    def _register_all_tools(self) -> None:
        # Tool 1: get_business_summary
        self._register(
            "get_business_summary",
            "Retrieves the business profile, industry, address, financial year, and currency.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                },
                "required": ["business_id"],
            },
            self._tool_get_business_summary,
        )

        # Tool 2: get_cash_position
        self._register(
            "get_cash_position",
            "Calculates live cash-in-hand, bank balances, and total available liquid funds.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                },
                "required": ["business_id"],
            },
            self._tool_get_cash_position,
        )

        # Tool 3: get_profit_and_loss
        self._register(
            "get_profit_and_loss",
            "Generates deterministic Profit & Loss statement (Gross Sales, COGS, OpEx, Net Profit).",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format (optional)"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format (optional)"},
                },
                "required": ["business_id"],
            },
            self._tool_get_profit_and_loss,
        )

        # Tool 4: get_cash_flow_statement
        self._register(
            "get_cash_flow_statement",
            "Generates Cash Flow statement categorized by Operating, Investing, and Financing activities.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                },
                "required": ["business_id"],
            },
            self._tool_get_cash_flow_statement,
        )

        # Tool 5: get_working_capital
        self._register(
            "get_working_capital",
            "Calculates Current Assets, Current Liabilities, Net Working Capital, and Current/Quick Ratios.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                },
                "required": ["business_id"],
            },
            self._tool_get_working_capital,
        )

        # Tool 6: get_ageing_report
        self._register(
            "get_ageing_report",
            "Analyzes customer receivables and supplier payables ageing buckets (0-30, 31-60, 61-90, 90+ days).",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                },
                "required": ["business_id"],
            },
            self._tool_get_ageing_report,
        )

        # Tool 7: get_customer_ledger
        self._register(
            "get_customer_ledger",
            "Retrieves a customer's running khata transaction statement, balance, and credit limit.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "customer_id": {"type": "string", "description": "UUID of the customer"},
                },
                "required": ["business_id", "customer_id"],
            },
            self._tool_get_customer_ledger,
        )

        # Tool 8: get_supplier_ledger
        self._register(
            "get_supplier_ledger",
            "Retrieves a supplier's running bill payment history and outstanding payables balance.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "supplier_id": {"type": "string", "description": "UUID of the supplier"},
                },
                "required": ["business_id", "supplier_id"],
            },
            self._tool_get_supplier_ledger,
        )

        # Tool 9: get_product_stock
        self._register(
            "get_product_stock",
            "Queries product catalog pricing, stock on hand, and unit cost.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "product_id": {"type": "string", "description": "UUID of the product"},
                },
                "required": ["business_id", "product_id"],
            },
            self._tool_get_product_stock,
        )

        # Tool 10: get_inventory_valuation
        self._register(
            "get_inventory_valuation",
            "Summarizes total inventory valuation and flags items below minimum stock alert.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "low_stock_only": {"type": "boolean", "description": "Filter to low stock items only"},
                },
                "required": ["business_id"],
            },
            self._tool_get_inventory_valuation,
        )

        # Tool 11: evaluate_decision_model
        self._register(
            "evaluate_decision_model",
            "Evaluates one of 8 versioned decision models (e.g. MACHINE_OR_EQUIPMENT_PURCHASE, NEW_PRODUCT_ADDITION).",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "model_id": {"type": "string", "description": "Model identifier"},
                    "inputs": {"type": "object", "description": "Model parameters dictionary"},
                },
                "required": ["business_id", "model_id", "inputs"],
            },
            self._tool_evaluate_decision_model,
        )

        # Tool 12: run_risk_simulation
        self._register(
            "run_risk_simulation",
            "Executes 1,000-iteration Monte Carlo risk simulation using NumPy PCG64 to compute P10/P50/P90.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "model_id": {"type": "string", "description": "Model identifier"},
                    "inputs": {"type": "object", "description": "Baseline parameters"},
                    "uncertainty_params": {"type": "object", "description": "Parameters to perturb with std dev"},
                },
                "required": ["business_id", "model_id", "inputs"],
            },
            self._tool_run_risk_simulation,
        )

        # Tool 13: run_sensitivity_analysis
        self._register(
            "run_sensitivity_analysis",
            "Runs deterministic One-at-a-Time (OAT) sensitivity analysis to compute Tornado chart swings.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "model_id": {"type": "string", "description": "Model identifier"},
                    "inputs": {"type": "object", "description": "Baseline parameters"},
                    "target_output_metric": {"type": "string", "description": "Output metric to analyze"},
                },
                "required": ["business_id", "model_id", "inputs", "target_output_metric"],
            },
            self._tool_run_sensitivity_analysis,
        )

        # Tool 14: get_business_health
        self._register(
            "get_business_health",
            "Computes composite 0-100 business health score across 5 pillars (Liquidity, Profitability, Solvency, Efficiency, Runway).",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                },
                "required": ["business_id"],
            },
            self._tool_get_business_health,
        )

        # Tool 15: get_goals_progress
        self._register(
            "get_goals_progress",
            "Evaluates real-time progress toward active revenue, profit, and debt reduction goals.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                },
                "required": ["business_id"],
            },
            self._tool_get_goals_progress,
        )

        # Tool 16: identify_data_gaps
        self._register(
            "identify_data_gaps",
            "Analyzes whether key facts are missing or contradictory for a requested decision or goal.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "decision_model": {"type": "string", "description": "Target decision model"},
                    "supplied_inputs": {"type": "object", "description": "Currently known inputs"},
                },
                "required": ["business_id", "decision_model"],
            },
            self._tool_identify_data_gaps,
        )

        # Tool 17: evaluate_cash_flow_pressure
        self._register(
            "evaluate_cash_flow_pressure",
            "Evaluates a 30-day cash pressure plan using explicitly supplied liquidity, receivables, payables, credit facility, and survival-threshold assumptions.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "inputs": {"type": "object", "description": "Explicit inputs required by the CASH_FLOW_PRESSURE evaluator"},
                },
                "required": ["business_id", "inputs"],
            },
            self._tool_evaluate_cash_flow_pressure,
        )

        # Tool 18: evaluate_business_viability
        self._register(
            "evaluate_business_viability",
            "Evaluates break-even, debt service, working capital, and a 12-month cash outlook from explicitly supplied business assumptions.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "inputs": {"type": "object", "description": "Explicit inputs required by the BUSINESS_VIABILITY evaluator"},
                },
                "required": ["business_id", "inputs"],
            },
            self._tool_evaluate_business_viability,
        )

        # Tool 19: check_unreconciled_inventory_costs
        self._register(
            "check_unreconciled_inventory_costs",
            "Lists inventory movements whose cost basis is unreconciled. Estimated impacts are informational and are not verified costs.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                },
                "required": ["business_id"],
            },
            self._tool_check_unreconciled_inventory_costs,
        )

        # Tool 20: run_scenario_simulation
        self._register(
            "run_scenario_simulation",
            "Runs and persists a seeded Monte Carlo simulation for a saved workspace scenario. Supply an explicit seed so the run can be reproduced.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "scenario_id": {"type": "string", "description": "UUID of the saved scenario"},
                    "iterations": {"type": "integer", "description": "Number of simulation iterations (1 to 100000)"},
                    "random_seed": {"type": "integer", "description": "Explicit unsigned 64-bit random seed"},
                    "distribution_config": {"type": "object", "description": "Optional explicit distribution overrides"},
                },
                "required": ["business_id", "scenario_id", "iterations", "random_seed"],
            },
            self._tool_run_scenario_simulation,
        )

        # Tool 21: replay_scenario_simulation
        self._register(
            "replay_scenario_simulation",
            "Replays a previously saved scenario simulation using its stored assumptions, distribution configuration, and seed, then verifies an exact result match.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "run_id": {"type": "string", "description": "UUID of the saved simulation run"},
                },
                "required": ["business_id", "run_id"],
            },
            self._tool_replay_scenario_simulation,
        )

        # Tool 22: analyze_goal_deviation
        self._register(
            "analyze_goal_deviation",
            "Compares a saved goal's ledger-derived actual performance with its dated plan and records an evidence-backed progress snapshot.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "goal_id": {"type": "string", "description": "UUID of the saved goal"},
                    "as_of_date": {"type": "string", "description": "Optional analysis date in YYYY-MM-DD format"},
                },
                "required": ["business_id", "goal_id"],
            },
            self._tool_analyze_goal_deviation,
        )

        # Tool 23: propose_agent_action
        self._register(
            "propose_agent_action",
            "Creates a confirmation-gated action proposal for this authenticated agent session. It never confirms or executes the action.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "action_type": {
                        "type": "string",
                        "enum": ["CREATE_GOAL", "CREATE_TASK", "GENERATE_REPORT"],
                        "description": "Supported proposed action type",
                    },
                    "payload": {"type": "object", "description": "Action details to be validated and stored pending explicit confirmation"},
                },
                "required": ["business_id", "action_type", "payload"],
            },
            self._tool_propose_agent_action,
        )

        # Tool 24: evaluate_investment_and_loan
        self._register(
            "evaluate_investment_and_loan",
            "Calculates deterministic compounding loan repayment, annualized CAGR, inflation-adjusted return, discounted debt service, real NPV, and liquidity coverage.",
            {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "UUID of the business workspace"},
                    "principal": {"type": "number", "description": "Principal loan or investment amount (e.g. 2000)"},
                    "interest_rate_pct": {"type": "number", "description": "Annual loan interest rate percent (e.g. 10)"},
                    "loan_tenure_years": {"type": "number", "description": "Loan repayment duration in years (e.g. 1)"},
                    "expected_return": {"type": "number", "description": "Total expected return or future value (e.g. 4000)"},
                    "return_horizon_years": {"type": "number", "description": "Investment return realization horizon in years (e.g. 4)"},
                    "inflation_rate_pct": {"type": "number", "description": "Annual inflation rate percent (e.g. 6)"},
                    "units": {"type": "number", "description": "Optional unit volume"},
                    "unit_cost": {"type": "number", "description": "Optional unit production or purchase cost"},
                    "unit_price": {"type": "number", "description": "Optional unit selling price"},
                    "fixed_costs": {"type": "number", "description": "Optional monthly or annual fixed costs"},
                    "capex": {"type": "number", "description": "Optional capital expenditure"},
                },
                "required": ["business_id"],
            },
            self._tool_evaluate_investment_and_loan,
        )

    # Handlers (Strictly Authorized & Business Isolated)
    def _tool_get_business_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        biz = self.business_service.business_repo.get_by_id(b_id)
        if not biz:
            return {"error": "Business workspace not found"}
        return {
            "business_id": str(biz.id),
            "name": biz.name,
            "industry": biz.industry,
            "address": biz.address,
            "currency": biz.currency,
            "financial_year_start": biz.financial_year_start,
        }

    def _tool_get_cash_position(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        return self.business_service.get_cash_position(b_id, u_id)

    def _tool_get_profit_and_loss(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        s_date = date.fromisoformat(args["start_date"]) if args.get("start_date") else date.today() - timedelta(days=90)
        e_date = date.fromisoformat(args["end_date"]) if args.get("end_date") else date.today()
        pnl = self.finance_engine.calculate_pnl(b_id, s_date, e_date).to_dict()
        rev = pnl.get("total_revenue", pnl.get("gross_sales", 0.0))
        opex = pnl.get("total_operating_expenses", 0.0)
        np = pnl.get("net_profit", 0.0)
        margin = pnl.get("net_margin_percent", 0.0)
        pnl["summary_line"] = f"Period Revenue: ₹{rev:,.2f}, Operating Expenses: ₹{opex:,.2f}, Net Profit: ₹{np:,.2f}, Net Margin: {margin:.1f}%"
        return pnl

    def _tool_get_cash_flow_statement(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        s_date = date.fromisoformat(args["start_date"]) if args.get("start_date") else date.today() - timedelta(days=90)
        e_date = date.fromisoformat(args["end_date"]) if args.get("end_date") else date.today()
        return self.finance_engine.calculate_cash_flow(b_id, s_date, e_date).to_dict()

    def _tool_get_working_capital(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        return self.finance_engine.calculate_working_capital(b_id).to_dict()

    def _tool_get_ageing_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        rec = self.finance_engine.calculate_receivables_ageing(b_id)
        pay = self.finance_engine.calculate_payables_ageing(b_id)
        return {"receivables": rec.to_dict(), "payables": pay.to_dict()}

    def _tool_get_customer_ledger(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        c_id = uuid.UUID(str(args["customer_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        cust = self.business_service.customer_repo.get_by_id(c_id)
        if not cust or cust.business_id != b_id:
            return {
                "error": f"Access denied: Customer {c_id} does not belong to authorized business {b_id}",
                "status": "FAILED",
            }
        return self.business_service.get_customer_ledger(b_id, c_id, u_id)

    def _tool_get_supplier_ledger(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        s_id = uuid.UUID(str(args["supplier_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        supp = self.business_service.supplier_repo.get_by_id(s_id)
        if not supp or supp.business_id != b_id:
            return {
                "error": f"Access denied: Supplier {s_id} does not belong to authorized business {b_id}",
                "status": "FAILED",
            }
        return self.business_service.get_supplier_ledger(b_id, s_id, u_id)

    def _tool_get_product_stock(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        p_id = uuid.UUID(str(args["product_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        prod = self.business_service.product_repo.get_by_id(p_id)
        if not prod or prod.business_id != b_id:
            return {
                "error": f"Access denied: Product {p_id} does not belong to authorized business {b_id}",
                "status": "FAILED",
            }
        bal = self.business_service.inventory_repo.get_balance(b_id, p_id)
        return {
            "product_id": str(prod.id),
            "name": prod.name,
            "quantity_on_hand": float(bal.quantity_on_hand) if bal else 0.0,
            "unit_cost": bal.unit_cost.to_float() if bal else 0.0,
            "total_valuation": bal.total_valuation.to_float() if bal else 0.0,
        }

    def _tool_get_inventory_valuation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        low_only = bool(args.get("low_stock_only", False))
        items = self.business_service.list_inventory_balances(b_id, u_id, low_stock_only=low_only)
        total_val = sum(it["total_valuation"] for it in items)
        return {
            "total_inventory_valuation": total_val,
            "total_tracked_products": len(items),
            "items": items,
        }

    def _tool_evaluate_decision_model(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        model_id = str(args["model_id"])
        inputs = dict(args.get("inputs", {}))
        return self.decision_engine.evaluate_decision(b_id, model_id, inputs).to_dict()

    def _tool_run_risk_simulation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        model_id = str(args["model_id"])
        inputs = dict(args.get("inputs", {}))
        uncertainty = dict(args.get("uncertainty_params", {}))
        return self.decision_engine.run_monte_carlo_simulation(b_id, model_id, inputs, uncertainty)

    def _tool_run_sensitivity_analysis(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        model_id = str(args["model_id"])
        inputs = dict(args.get("inputs", {}))
        metric = str(args["target_output_metric"])
        points = self.decision_engine.run_sensitivity_analysis(b_id, model_id, inputs, metric)
        return {"target_metric": metric, "ranked_tornado_points": points}

    def _tool_get_business_health(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        return self.finance_engine.compute_health_score(b_id).to_dict()

    def _tool_get_goals_progress(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        goals = self.business_service.goal_repo.list_by_business(b_id)
        return {
            "goals": [
                {
                    "title": g.title,
                    "target_value": float(g.target_value),
                    "current_value": float(g.current_value),
                    "progress_percent": float(g.progress_percent),
                    "status": g.status.value,
                }
                for g in goals
            ]
        }

    def _tool_identify_data_gaps(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        model = str(args.get("decision_model", ""))
        known = dict(args.get("supplied_inputs", {}))
        required_keys = {
            "MACHINE_OR_EQUIPMENT_PURCHASE": ["machine_cost", "down_payment", "unit_price", "unit_variable_cost"],
            "NEW_PRODUCT_ADDITION": ["selling_price", "variable_cost", "expected_monthly_volume"],
            "SUPPLIER_SWITCH_OR_CREDIT_TERMS": ["current_unit_price", "new_unit_price", "monthly_units"],
        }.get(model, ["cost", "revenue"])

        missing = [k for k in required_keys if k not in known or known[k] is None or known[k] <= 0]
        has_gaps = len(missing) > 0
        questions = [f"What is the expected {k.replace('_', ' ')}?" for k in missing]

        return {
            "decision_model": model,
            "has_data_gaps": has_gaps,
            "missing_inputs": missing,
            "follow_up_questions": questions,
        }

    @staticmethod
    def _finance_edit_roles() -> List[BusinessRole]:
        return [BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT]

    def _tool_evaluate_cash_flow_pressure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id, self._finance_edit_roles())
        return self.decision_engine.evaluate_decision(
            b_id, "CASH_FLOW_PRESSURE", dict(args.get("inputs") or {})
        ).to_dict()

    def _tool_evaluate_business_viability(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id, self._finance_edit_roles())
        return self.decision_engine.evaluate_decision(
            b_id, "BUSINESS_VIABILITY", dict(args.get("inputs") or {})
        ).to_dict()

    def _tool_check_unreconciled_inventory_costs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        service = self.inventory_cost_service
        if service is None:
            from backend.arthlens.services.inventory_cost_service import InventoryCostService
            service = InventoryCostService()
            self.inventory_cost_service = service
        result = service.list_unreconciled_inventory_movements(b_id)
        return {**result, "cost_estimates_are_verified": False}

    def _tool_run_scenario_simulation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id, self._finance_edit_roles())
        from decimal import InvalidOperation
        try:
            iterations_decimal = Decimal(str(args["iterations"]))
            seed_decimal = Decimal(str(args["random_seed"]))
            if (
                isinstance(args["iterations"], bool)
                or isinstance(args["random_seed"], bool)
                or not iterations_decimal.is_finite()
                or not seed_decimal.is_finite()
                or iterations_decimal != iterations_decimal.to_integral_value()
                or seed_decimal != seed_decimal.to_integral_value()
            ):
                raise ValueError
            iterations, random_seed = int(iterations_decimal), int(seed_decimal)
        except (InvalidOperation, TypeError, ValueError, KeyError):
            return {"error": "iterations and random_seed must be integers", "status": "FAILED"}
        service = self.scenario_service
        if service is None:
            from backend.arthlens.services.scenario_service import get_scenario_service
            service = get_scenario_service()
            self.scenario_service = service
        return service.run_monte_carlo(
            b_id,
            uuid.UUID(str(args["scenario_id"])),
            u_id,
            iterations,
            random_seed,
            args.get("distribution_config"),
        )

    def _tool_replay_scenario_simulation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)
        service = self.scenario_service
        if service is None:
            from backend.arthlens.services.scenario_service import get_scenario_service
            service = get_scenario_service()
            self.scenario_service = service
        return service.replay(b_id, uuid.UUID(str(args["run_id"])))

    def _tool_analyze_goal_deviation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id, self._finance_edit_roles())
        as_of_date = date.fromisoformat(args["as_of_date"]) if args.get("as_of_date") else None
        service = self.goal_planning_service
        if service is None:
            from backend.arthlens.services.goal_planning_service import get_goal_planning_service
            service = get_goal_planning_service()
            self.goal_planning_service = service
        return service.evaluate_goal_progress(
            b_id,
            uuid.UUID(str(args["goal_id"])),
            u_id,
            as_of_date,
        )

    def _tool_propose_agent_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        session_id = args.get("_trusted_session_id")
        if not session_id:
            return {"error": "An authenticated agent session is required to propose an action", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id, self._finance_edit_roles())
        service = self.agent_action_service
        if service is None:
            from backend.arthlens.services.agent_action_service import get_agent_action_service
            service = get_agent_action_service()
            self.agent_action_service = service
        proposal = service.create(
            b_id,
            uuid.UUID(str(session_id)),
            u_id,
            str(args["action_type"]).upper(),
            dict(args.get("payload") or {}),
        )
        if proposal.get("status") != "PENDING_CONFIRMATION":
            return {"error": "Action service did not create a confirmation-gated proposal", "status": "ERROR"}
        return proposal

    def _tool_evaluate_investment_and_loan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("user_id"):
            return {"error": "Authentication required: user_id is mandatory", "status": "FAILED"}
        b_id = uuid.UUID(str(args["business_id"]))
        u_id = uuid.UUID(str(args["user_id"]))
        self.business_service.verify_access(b_id, u_id)

        principal = float(args.get("principal", args.get("loan_amount", args.get("loan_principal", 2000.0))))
        interest_rate_pct = float(args.get("interest_rate_pct", args.get("loan_interest_rate_pct", 10.0)))
        loan_tenure_years = float(args.get("loan_tenure_years", 1.0))
        expected_return = float(args.get("expected_return", args.get("future_value", args.get("investment_return", 4000.0))))
        return_horizon_years = float(args.get("return_horizon_years", args.get("investment_horizon_years", 4.0)))
        inflation_rate_pct = float(args.get("inflation_rate_pct", 6.0))

        cash_pos = self.business_service.get_cash_position(b_id, u_id)
        workspace_liquid_cash = float(cash_pos.get("total_liquidity", 0.0))

        total_repayment = principal * ((1.0 + interest_rate_pct / 100.0) ** loan_tenure_years)
        interest_cost = total_repayment - principal
        nominal_net_profit = expected_return - total_repayment
        annualized_cagr_pct = (((expected_return / max(principal, 0.0001)) ** (1.0 / max(return_horizon_years, 0.0001))) - 1.0) * 100.0 if principal > 0 else 0.0
        inflation_adjusted_return = expected_return / ((1.0 + inflation_rate_pct / 100.0) ** return_horizon_years)
        discounted_repayment = total_repayment / ((1.0 + inflation_rate_pct / 100.0) ** loan_tenure_years)
        real_npv = inflation_adjusted_return - discounted_repayment
        liquidity_coverage = bool(workspace_liquid_cash >= total_repayment)

        is_feasible = (real_npv > 0) and (annualized_cagr_pct > max(interest_rate_pct, inflation_rate_pct))
        verdict = "PROCEED" if is_feasible else "DO NOT PROCEED"

        return {
            "principal": round(principal, 2),
            "interest_rate_pct": round(interest_rate_pct, 2),
            "loan_tenure_years": round(loan_tenure_years, 2),
            "expected_return": round(expected_return, 2),
            "return_horizon_years": round(return_horizon_years, 2),
            "inflation_rate_pct": round(inflation_rate_pct, 2),
            "total_repayment": round(total_repayment, 2),
            "interest_cost": round(interest_cost, 2),
            "nominal_net_profit": round(nominal_net_profit, 2),
            "annualized_cagr_pct": round(annualized_cagr_pct, 2),
            "inflation_adjusted_return": round(inflation_adjusted_return, 2),
            "discounted_repayment": round(discounted_repayment, 2),
            "real_npv": round(real_npv, 2),
            "workspace_liquid_cash": round(workspace_liquid_cash, 2),
            "liquidity_coverage": liquidity_coverage,
            "verdict": verdict,
            "units": float(args.get("units", 0.0)),
            "unit_cost": float(args.get("unit_cost", 0.0)),
            "unit_price": float(args.get("unit_price", 0.0)),
            "fixed_costs": float(args.get("fixed_costs", 0.0)),
            "capex": float(args.get("capex", 0.0)),
            "status": "SUCCESS",
        }
