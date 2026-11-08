"""Unit tests for structured government scheme rules: PMFME, PMEGP, and PM-MUDRA."""

import pytest
from backend.arthlens.policy.rules import TruthValue
from backend.arthlens.policy.scheme_rules import (
    MUDRA_RULE_SET,
    PMEGP_RULE_SET,
    PMFME_RULE_SET,
    SCHEME_REGISTRY,
    FinancialMechanism,
    SchemeApprovalStatus,
    get_scheme_rule_set,
)


@pytest.mark.unit
def test_all_three_schemes_registered_with_official_hashes():
    assert len(SCHEME_REGISTRY) == 3
    for scheme_id in ("scheme:pmfme:v1", "scheme:pmegp:v1", "scheme:pm_mudra:v1"):
        scheme = get_scheme_rule_set(scheme_id)
        assert scheme is not None
        assert scheme.scheme_id == scheme_id
        assert scheme.source_document
        assert len(scheme.source_document_hash) == 64  # SHA-256
        assert scheme.required_evidence
        assert scheme.known_ambiguities
        # Crucial guardrail: must NOT be approved without human authorization
        assert scheme.approval_status == SchemeApprovalStatus.UNAPPROVED
        assert scheme.is_approved_for_advice is False


@pytest.mark.unit
def test_pmfme_eligibility_and_financial_parameters():
    scheme = PMFME_RULE_SET
    assert scheme.financial_mechanism == FinancialMechanism.CAPITAL_SUBSIDY
    params = scheme.financial_parameters
    assert params["subsidy_fraction"] == 0.35
    assert params["max_subsidy_inr"] == 1000000.0
    assert params["min_beneficiary_contribution_fraction"] == 0.10
    assert params["lock_in_years"] == 3

    # 1. Eligible applicant
    eligible_facts = {
        "applicant.age": 28,
        "enterprise.sector": "food_processing",
        "enterprise.is_micro": True,
        "enterprise.in_negative_list": False,
        "beneficiary.own_contribution_fraction": 0.15,
    }
    assert scheme.evaluate_eligibility(eligible_facts) == TruthValue.TRUE

    # 2. Ineligible: in negative list
    negative_facts = dict(eligible_facts, **{"enterprise.in_negative_list": True})
    assert scheme.evaluate_eligibility(negative_facts) == TruthValue.FALSE

    # 3. Missing facts: unknown sector
    missing_facts = {
        "applicant.age": 28,
        "enterprise.is_micro": True,
    }
    assert scheme.evaluate_eligibility(missing_facts) == TruthValue.UNKNOWN


@pytest.mark.unit
def test_pmegp_eligibility_and_education_threshold():
    scheme = PMEGP_RULE_SET
    assert scheme.financial_mechanism == FinancialMechanism.MARGIN_MONEY
    params = scheme.financial_parameters
    assert params["max_admissible_cost_manufacturing_inr"] == 5000000.0
    assert params["max_admissible_cost_service_inr"] == 2000000.0
    assert params["special_rural_subsidy_fraction"] == 0.35

    # 1. Below project cost threshold: education not required
    small_project_facts = {
        "applicant.age": 22,
        "enterprise.is_new_unit": True,
        "enterprise.in_negative_list": False,
        "applicant.project_cost_exceeds_education_threshold": False,
    }
    assert scheme.evaluate_eligibility(small_project_facts) == TruthValue.TRUE

    # 2. Above threshold without 8th pass qualification: Ineligible
    large_project_unqualified = {
        "applicant.age": 30,
        "enterprise.is_new_unit": True,
        "enterprise.in_negative_list": False,
        "applicant.project_cost_exceeds_education_threshold": True,
        "applicant.education_level": "uneducated",
    }
    assert scheme.evaluate_eligibility(large_project_unqualified) == TruthValue.FALSE

    # 3. Above threshold with 10th pass qualification: Eligible
    large_project_qualified = dict(large_project_unqualified, **{"applicant.education_level": "10th_pass"})
    assert scheme.evaluate_eligibility(large_project_qualified) == TruthValue.TRUE


@pytest.mark.unit
def test_mudra_eligibility_and_tarun_plus_expansion():
    scheme = MUDRA_RULE_SET
    assert scheme.financial_mechanism == FinancialMechanism.CREDIT_FACILITY
    params = scheme.financial_parameters
    assert params["shishu_max_loan_inr"] == 50000.0
    assert params["tarun_max_loan_inr"] == 1000000.0
    assert params["tarun_plus_max_loan_inr"] == 2000000.0  # 2024 expansion

    # 1. Kishor applicant: good track record
    kishor_facts = {
        "enterprise.is_non_farm": True,
        "enterprise.is_non_corporate": True,
        "applicant.is_defaulter": False,
        "loan.category_requested": "kishor",
    }
    assert scheme.evaluate_eligibility(kishor_facts) == TruthValue.TRUE

    # 2. Tarun Plus applicant without previous Tarun repayment: Ineligible
    tarun_plus_no_repay = {
        "enterprise.is_non_farm": True,
        "enterprise.is_non_corporate": True,
        "applicant.is_defaulter": False,
        "loan.category_requested": "tarun_plus",
        "borrower.fully_repaid_previous_tarun": False,
    }
    assert scheme.evaluate_eligibility(tarun_plus_no_repay) == TruthValue.FALSE

    # 3. Tarun Plus with verified repayment: Eligible
    tarun_plus_verified = dict(tarun_plus_no_repay, **{"borrower.fully_repaid_previous_tarun": True})
    assert scheme.evaluate_eligibility(tarun_plus_verified) == TruthValue.TRUE
