from decimal import Decimal
from types import SimpleNamespace
import uuid

from backend.arthlens.decision.engine import DecisionIntelligenceEngine
from backend.arthlens.domain.business import DecisionEvaluation, Money


class FinanceStub:
    def calculate_working_capital(self, business_id):
        return SimpleNamespace(cash_and_bank=Money(Decimal("1200.00")))

    def calculate_pnl(self, business_id, start_date, end_date):
        return SimpleNamespace(operating_profit_ebitda=Money(Decimal("600.00")))


class DecisionRepositoryStub:
    def __init__(self):
        self.saved = None

    def save(self, evaluation: DecisionEvaluation):
        self.saved = evaluation
        return evaluation


def test_decision_evaluation_persists_graph_evidence_and_immutable_version_metadata():
    repository = DecisionRepositoryStub()
    engine = DecisionIntelligenceEngine(decision_repo=repository, finance_engine=FinanceStub())
    business_id = uuid.uuid4()

    result = engine.evaluate_decision(
        business_id,
        "NEW_PRODUCT_ADDITION",
        {
            "product_name": "Test product", "selling_price": "100.00", "variable_cost": "40.00",
            "expected_monthly_volume": "200", "setup_cost": "500", "cannibalization_rate": "0",
            "input_provenance": {"product_name": "USER_ASSUMPTION"},
        },
        save_evaluation=True,
    )

    assert result.evaluation_id == str(repository.saved.id)
    assert result.version_number == 1
    assert repository.saved.causal_graph["nodes"]
    assert {item["source_type"] for item in repository.saved.evidence_items} >= {"USER_ASSUMPTION", "LEDGER_ACTUAL"}
    assert all("input_provenance" not in item["label"] for item in repository.saved.evidence_items)


def test_nested_location_parameters_get_path_level_user_provenance():
    engine = DecisionIntelligenceEngine(decision_repo=DecisionRepositoryStub(), finance_engine=FinanceStub())

    enriched = engine._enrich_financial_inputs(uuid.uuid4(), {
        "candidates": [{"location_name": "Site A", "monthly_rent": "4500.00"}],
        "input_provenance": {"candidates": "USER_ASSUMPTION"},
    })

    assert enriched["input_provenance"]["candidates[0].location_name"] == "USER_ASSUMPTION"
    assert enriched["input_provenance"]["candidates[0].monthly_rent"] == "USER_ASSUMPTION"
    assert enriched["input_provenance"]["current_cash_liquidity"] == "LEDGER_ACTUAL"
