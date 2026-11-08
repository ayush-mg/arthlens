"""
Authoritative Structured Government Scheme Rules: PMFME, PMEGP, and PM-MUDRA.

Authoritative Reference:
- ArthLens Build Handbook v1.0 (Section 2.1, 2.2 #10, 6.8, 13.1 P0-2).
- Source Documents:
  * PMFME: MoFPI Guidelines (PMFME_Scheme_Guidelines_English.pdf)
  * PMEGP: KVIC/MSME Notification (PMEGP_MSME_Official_Notification.pdf)
  * PM-MUDRA: DFS Circular (PMMY_Tarun_Plus_Notification_2024.pdf)
- Crucial Rule: All scheme rules in this module represent source-supported extractions.
  They are marked as UNAPPROVED until formal qualified human verification is recorded.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from backend.arthlens.policy.rules import (
    AllOfNode,
    AnyOfNode,
    Comparison,
    NotNode,
    PredicateNode,
    RuleNode,
    TruthValue,
)
from backend.arthlens.policy.visitors import EligibilityEvaluator, EvaluationTrace


def extract_required_facts(node: RuleNode) -> set[str]:
    """Recursively collect all fact names required by an AST."""
    facts = set()
    if isinstance(node, PredicateNode):
        facts.add(node.fact)
    elif isinstance(node, (AllOfNode, AnyOfNode)):
        for child in node.children:
            facts.update(extract_required_facts(child))
    elif isinstance(node, NotNode):
        facts.update(extract_required_facts(node.child))
    return facts


class SchemeApprovalStatus(str, Enum):
    UNAPPROVED = "UNAPPROVED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    APPROVED = "APPROVED"


class FinancialMechanism(str, Enum):
    CAPITAL_SUBSIDY = "CAPITAL_SUBSIDY"
    MARGIN_MONEY = "MARGIN_MONEY"
    CREDIT_FACILITY = "CREDIT_FACILITY"
    CREDIT_GUARANTEE = "CREDIT_GUARANTEE"


@dataclass(frozen=True)
class SchemeRuleSet:
    """Complete structured representation of a government financial scheme."""

    scheme_id: str
    official_name: str
    publisher: str
    source_document: str
    source_document_hash: str
    effective_start: str
    effective_end: str | None
    financial_mechanism: FinancialMechanism
    target_enterprise_category: str
    eligibility_ast: RuleNode
    financial_parameters: Mapping[str, Any]
    required_evidence: tuple[str, ...]
    approval_status: SchemeApprovalStatus = SchemeApprovalStatus.UNAPPROVED
    approved_by: str | None = None
    approval_date: str | None = None
    known_ambiguities: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_approved_for_advice(self) -> bool:
        """Fails closed: unapproved rules must never claim official certification."""
        return self.approval_status == SchemeApprovalStatus.APPROVED

    def evaluate_eligibility(self, facts: Mapping[str, Any]) -> TruthValue:
        """Evaluate applicant facts using Kleene 3-valued logic, returning TruthValue."""
        evaluator = EligibilityEvaluator(facts)
        trace = evaluator.evaluate(self.eligibility_ast)
        return trace.result

    def evaluate_eligibility_trace(self, facts: Mapping[str, Any]) -> EvaluationTrace:
        """Evaluate applicant facts and return the complete explainable EvaluationTrace."""
        evaluator = EligibilityEvaluator(facts)
        return evaluator.evaluate(self.eligibility_ast)

    def list_required_facts(self) -> set[str]:
        """Collect all fact names required by the eligibility AST."""
        return extract_required_facts(self.eligibility_ast)


# ==============================================================================
# 1. PMFME (Pradhan Mantri Formalisation of Micro food processing Enterprises)
# ==============================================================================

PMFME_ELIGIBILITY_AST = AllOfNode(
    children=(
        PredicateNode(fact="applicant.age", comparison=Comparison.GTE, expected=18),
        PredicateNode(fact="enterprise.sector", comparison=Comparison.EQ, expected="food_processing"),
        PredicateNode(fact="enterprise.is_micro", comparison=Comparison.EQ, expected=True),
        PredicateNode(fact="enterprise.in_negative_list", comparison=Comparison.EQ, expected=False),
        PredicateNode(fact="beneficiary.own_contribution_fraction", comparison=Comparison.GTE, expected=0.10),
    )
)

PMFME_RULE_SET = SchemeRuleSet(
    scheme_id="scheme:pmfme:v1",
    official_name="Pradhan Mantri Formalisation of Micro food processing Enterprises (PMFME)",
    publisher="Ministry of Food Processing Industries (MoFPI), Government of India",
    source_document="PMFME_Scheme_Guidelines_English.pdf",
    source_document_hash="632c359d08289866abb104c642b0efb1bf9e007baf06b651a13fd0de47f90ce8",
    effective_start="2020-06-29",
    effective_end="2026-03-31",
    financial_mechanism=FinancialMechanism.CAPITAL_SUBSIDY,
    target_enterprise_category="Existing and new individual micro food processing units (<10 workers)",
    eligibility_ast=PMFME_ELIGIBILITY_AST,
    financial_parameters={
        "subsidy_fraction": 0.35,  # 35% of eligible project cost
        "max_subsidy_inr": 1000000.0,  # ₹10 Lakh ceiling
        "min_beneficiary_contribution_fraction": 0.10,  # 10% own equity
        "lock_in_years": 3,  # Kept in Subsidy Reserve Fund for 3 years
        "shg_seed_capital_per_member_inr": 40000.0,
    },
    required_evidence=(
        "proof.identity",
        "proof.enterprise_ownership_or_lease",
        "proof.food_processing_activity",
        "proof.own_equity_deposit",
    ),
    approval_status=SchemeApprovalStatus.UNAPPROVED,
    known_ambiguities=(
        "Whether non-ODOP existing units receive the full 35% subsidy across all state variations.",
        "Treatment of GST registration exemption for micro food processing units below turnover threshold.",
    ),
)


# ==============================================================================
# 2. PMEGP (Prime Minister's Employment Generation Programme)
# ==============================================================================

# Education requirement applies only if manufacturing cost > 10L or service cost > 5L
PMEGP_ELIGIBILITY_AST = AllOfNode(
    children=(
        PredicateNode(fact="applicant.age", comparison=Comparison.GTE, expected=18),
        PredicateNode(fact="enterprise.is_new_unit", comparison=Comparison.EQ, expected=True),
        PredicateNode(fact="enterprise.in_negative_list", comparison=Comparison.EQ, expected=False),
        # Qualification condition: if above threshold, must have at least 8th standard pass
        AnyOfNode(
            children=(
                PredicateNode(fact="applicant.project_cost_exceeds_education_threshold", comparison=Comparison.EQ, expected=False),
                PredicateNode(
                    fact="applicant.education_level",
                    comparison=Comparison.IN,
                    expected=("8th_pass", "10th_pass", "12th_pass", "graduate", "postgraduate"),
                ),
            )
        ),
    )
)

PMEGP_RULE_SET = SchemeRuleSet(
    scheme_id="scheme:pmegp:v1",
    official_name="Prime Minister's Employment Generation Programme (PMEGP)",
    publisher="Ministry of Micro, Small & Medium Enterprises (MoMSME) / KVIC",
    source_document="PMEGP_MSME_Official_Notification.pdf",
    source_document_hash="90e9d90f6c61ee8c81dc6125a24cc3389e391987cd404c0d81f085a96e9d21fb",
    effective_start="2022-05-30",
    effective_end="2026-03-31",
    financial_mechanism=FinancialMechanism.MARGIN_MONEY,
    target_enterprise_category="New micro enterprises in manufacturing and business/service sectors",
    eligibility_ast=PMEGP_ELIGIBILITY_AST,
    financial_parameters={
        "max_admissible_cost_manufacturing_inr": 5000000.0,  # ₹50 Lakh
        "max_admissible_cost_service_inr": 2000000.0,  # ₹20 Lakh
        "general_urban_subsidy_fraction": 0.15,
        "general_urban_own_equity_fraction": 0.10,
        "general_rural_subsidy_fraction": 0.25,
        "general_rural_own_equity_fraction": 0.10,
        "special_urban_subsidy_fraction": 0.25,
        "special_urban_own_equity_fraction": 0.05,
        "special_rural_subsidy_fraction": 0.35,  # 35% max margin money
        "special_rural_own_equity_fraction": 0.05,
        "lock_in_years": 3,
        "mandatory_udyam_registration": True,
        "mandatory_edp_training": True,
    },
    required_evidence=(
        "proof.identity",
        "proof.age",
        "proof.education_certificate",
        "proof.project_dpr",
        "proof.special_category_certificate_if_applicable",
    ),
    approval_status=SchemeApprovalStatus.UNAPPROVED,
    known_ambiguities=(
        "PMEGP guidelines span the 15th Finance Commission cycle to FY 2025-26; post-2026 extension circular must be confirmed.",
        "Classification of semi-urban census towns as rural vs urban under local KVIC bank branches.",
    ),
)


# ==============================================================================
# 3. PM-MUDRA (Pradhan Mantri Mudra Yojana)
# ==============================================================================

MUDRA_ELIGIBILITY_AST = AllOfNode(
    children=(
        PredicateNode(fact="enterprise.is_non_farm", comparison=Comparison.EQ, expected=True),
        PredicateNode(fact="enterprise.is_non_corporate", comparison=Comparison.EQ, expected=True),
        PredicateNode(fact="applicant.is_defaulter", comparison=Comparison.EQ, expected=False),
        # If Tarun Plus (> 10L up to 20L), borrower must have repaid previous Tarun loan
        AnyOfNode(
            children=(
                PredicateNode(fact="loan.category_requested", comparison=Comparison.IN, expected=("shishu", "kishor", "tarun")),
                AllOfNode(
                    children=(
                        PredicateNode(fact="loan.category_requested", comparison=Comparison.EQ, expected="tarun_plus"),
                        PredicateNode(fact="borrower.fully_repaid_previous_tarun", comparison=Comparison.EQ, expected=True),
                    )
                ),
            )
        ),
    )
)

MUDRA_RULE_SET = SchemeRuleSet(
    scheme_id="scheme:pm_mudra:v1",
    official_name="Pradhan Mantri Mudra Yojana (PMMY)",
    publisher="Department of Financial Services (DFS), Ministry of Finance, Government of India",
    source_document="PMMY_Tarun_Plus_Notification_2024.pdf",
    source_document_hash="601c7bf54125b2f29b47e24483b87431f4ba512b9d21f8a85f8c857753e1a0d8",
    effective_start="2024-10-25",
    effective_end=None,  # Ongoing statutory credit programme
    financial_mechanism=FinancialMechanism.CREDIT_FACILITY,
    target_enterprise_category="Non-corporate, non-farm micro and small enterprises",
    eligibility_ast=MUDRA_ELIGIBILITY_AST,
    financial_parameters={
        "shishu_max_loan_inr": 50000.0,
        "kishor_min_loan_inr": 50001.0,
        "kishor_max_loan_inr": 500000.0,
        "tarun_min_loan_inr": 500001.0,
        "tarun_max_loan_inr": 1000000.0,
        "tarun_plus_min_loan_inr": 1000001.0,
        "tarun_plus_max_loan_inr": 2000000.0,  # Expanded to ₹20L in Oct 2024
        "collateral_required": False,  # Collateral-free credit backed by CGFMU
    },
    required_evidence=(
        "proof.identity",
        "proof.business_address",
        "proof.bank_statement",
        "proof.past_repayment_record_if_tarun_plus",
    ),
    approval_status=SchemeApprovalStatus.UNAPPROVED,
    known_ambiguities=(
        "Exact margin requirement for Kishor and Tarun varies between commercial banks up to 15%.",
        "Lending interest rate benchmarked to bank MCLR/EBLR without uniform statutory cap.",
    ),
)

SCHEME_REGISTRY: dict[str, SchemeRuleSet] = {
    PMFME_RULE_SET.scheme_id: PMFME_RULE_SET,
    PMEGP_RULE_SET.scheme_id: PMEGP_RULE_SET,
    MUDRA_RULE_SET.scheme_id: MUDRA_RULE_SET,
}


def get_scheme_rule_set(scheme_id: str) -> SchemeRuleSet | None:
    """Retrieve structured scheme rule set by canonical scheme ID."""
    return SCHEME_REGISTRY.get(scheme_id)
