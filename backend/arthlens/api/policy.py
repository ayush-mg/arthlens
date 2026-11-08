"""Source-backed scheme policy registry and three-valued eligibility evaluation."""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.arthlens.domain.enums import Kind
from backend.arthlens.infra.repositories import (
    PostgresPolicyRuleRepository,
    PostgresQuantityRepository,
    PostgresSourceRepository,
)
from backend.arthlens.policy.serialization import parse_rule_ast, rule_facts, serialize_rule_ast
from backend.arthlens.policy.visitors import EligibilityEvaluator, EvaluationTrace
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(prefix="/policy", tags=["Policy Rules"])
_HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_ALL_ROLES = (Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)


class RegisterPolicyDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheme_id: str = Field(min_length=1, max_length=100)
    source_version_id: str = Field(min_length=1, max_length=300)


class ReviewPolicyDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verified: bool
    review_note: str = Field(min_length=20, max_length=2000)


class EvidenceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_key: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=100)
    allowed_kinds: List[str] = Field(min_length=1)
    minimum_evidence_floor: int = Field(ge=1, le=4)


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: uuid.UUID
    locator: str = Field(min_length=1, max_length=500)


class CreatePolicyRuleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    scheme_id: str = Field(min_length=1, max_length=100)
    rule_key: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    rule_ast: Dict[str, Any]
    evidence_requirements: Dict[str, EvidenceRequirement]
    source_references: List[SourceReference] = Field(min_length=1)
    effective_from: date
    effective_to: Optional[date] = None


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_note: str = Field(min_length=20, max_length=2000)


class RetirementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retirement_reason: str = Field(min_length=20, max_length=2000)


class PolicyEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_key: str = Field(min_length=1, max_length=200)
    as_of: date
    fact_quantity_ids: Dict[str, uuid.UUID]


@router.post("/documents", status_code=status.HTTP_201_CREATED)
def register_policy_document(
    body: RegisterPolicyDocumentRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.STEWARD)),
) -> Dict[str, Any]:
    """Register a policy document against an existing source snapshot; no user claims are copied."""
    source_repo = PostgresSourceRepository()
    version = source_repo.get_version(body.source_version_id)
    if version is None or version.get("status") != "ACTIVE":
        raise HTTPException(status_code=422, detail="An active registered source version is required.")
    source = source_repo.get_source(version["source_id"])
    source_url = version.get("source_url")
    content_hash = version.get("content_hash")
    if (
        source is None
        or source.get("status") != "ACTIVE"
        or not isinstance(source_url, str)
        or not source_url.strip()
        or not isinstance(content_hash, str)
        or not _HEX_SHA256.fullmatch(content_hash)
    ):
        raise HTTPException(
            status_code=422,
            detail="The source registry lacks an active URL and valid SHA-256 snapshot for this version.",
        )
    repo = PostgresPolicyRuleRepository()
    document_id = repo.save_document({
        "scheme_id": body.scheme_id,
        "source_version_id": version["id"],
        "document_url": source_url,
        "sha256": content_hash.lower(),
    })
    get_audit_service().record_event(
        current_user.id,
        "POLICY_DOCUMENT_REGISTERED",
        f"policy_document:{document_id}",
        {"scheme_id": body.scheme_id, "source_version_id": version["id"]},
    )
    return repo.get_document(document_id) or {"id": document_id, "status": "PENDING_REVIEW"}


@router.post("/documents/{document_id}/review")
def review_policy_document(
    document_id: uuid.UUID,
    body: ReviewPolicyDocumentRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.STEWARD)),
) -> Dict[str, Any]:
    repo = PostgresPolicyRuleRepository()
    try:
        record = repo.review_document(
            document_id,
            reviewer_id=current_user.id,
            verified=body.verified,
            review_note=body.review_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Policy document not found.")
    get_audit_service().record_event(
        current_user.id,
        "POLICY_DOCUMENT_REVIEWED",
        f"policy_document:{document_id}",
        {"status": record["status"], "source_version_id": record["source_version_id"]},
    )
    return record


@router.get("/rules")
def list_policy_rules(
    scheme_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_roles(*_ALL_ROLES)),
) -> List[Dict[str, Any]]:
    repo = PostgresPolicyRuleRepository()
    rules = repo.list_rules_by_scheme(scheme_id) if scheme_id else []
    if Role.STEWARD.value not in current_user.roles and Role.ADMIN.value not in current_user.roles:
        rules = [rule for rule in rules if rule.get("status") in ("APPROVED", "RETIRED")]
    return rules


@router.post("/rules", status_code=status.HTTP_201_CREATED)
def create_policy_rule(
    body: CreatePolicyRuleRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.STEWARD)),
) -> Dict[str, Any]:
    try:
        node = parse_rule_ast(body.rule_ast)
        facts = rule_facts(node)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid policy AST: {exc}") from exc
    if facts != frozenset(body.evidence_requirements):
        raise HTTPException(
            status_code=422,
            detail="Evidence requirements must map exactly to every predicate fact in the rule AST.",
        )
    if body.effective_to is not None and body.effective_to < body.effective_from:
        raise HTTPException(status_code=422, detail="effective_to must not precede effective_from.")
    normalized_requirements: Dict[str, Dict[str, Any]] = {}
    valid_kinds = {kind.value for kind in Kind}
    for fact, requirement in body.evidence_requirements.items():
        kinds = requirement.allowed_kinds
        if not kinds or len(set(kinds)) != len(kinds) or not set(kinds) <= valid_kinds:
            raise HTTPException(status_code=422, detail=f"Invalid allowed_kinds for predicate {fact!r}.")
        normalized_requirements[fact] = requirement.model_dump()

    repo = PostgresPolicyRuleRepository()
    citations = []
    for citation in body.source_references:
        document = repo.get_document(citation.document_id)
        if document is None or document.get("scheme_id") != body.scheme_id:
            raise HTTPException(status_code=422, detail="Every source reference must identify a registered document for this scheme.")
        citations.append({
            "document_id": document["id"],
            "source_version_id": document["source_version_id"],
            "document_url": document["document_url"],
            "sha256": document["sha256"],
            "locator": citation.locator,
        })
    try:
        rule_id = repo.save_rule({
            "scheme_id": body.scheme_id,
            "rule_key": body.rule_key,
            "version": body.version,
            "rule_ast": serialize_rule_ast(node),
            "evidence_requirements": normalized_requirements,
            "source_references": citations,
            "effective_from": body.effective_from,
            "effective_to": body.effective_to,
        })
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    get_audit_service().record_event(
        current_user.id,
        "POLICY_RULE_DRAFT_CREATED",
        f"policy_rule:{rule_id}",
        {"scheme_id": body.scheme_id, "rule_key": body.rule_key, "version": body.version},
    )
    return repo.get_rule(rule_id) or {"id": rule_id, "status": "DRAFT"}


@router.post("/rules/{rule_id}/approve")
def approve_policy_rule(
    rule_id: uuid.UUID,
    body: ApprovalRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.STEWARD)),
) -> Dict[str, Any]:
    repo = PostgresPolicyRuleRepository()
    try:
        record = repo.approve_rule(rule_id, steward_id=current_user.id, approval_note=body.approval_note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Policy rule not found.")
    get_audit_service().record_event(
        current_user.id,
        "POLICY_RULE_APPROVED",
        f"policy_rule:{rule_id}",
        {"scheme_id": record["scheme_id"], "rule_key": record["rule_key"], "version": record["version"]},
    )
    return record


@router.post("/rules/{rule_id}/retire")
def retire_policy_rule(
    rule_id: uuid.UUID,
    body: RetirementRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.STEWARD)),
) -> Dict[str, Any]:
    repo = PostgresPolicyRuleRepository()
    try:
        record = repo.retire_rule(
            rule_id,
            steward_id=current_user.id,
            retirement_reason=body.retirement_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Policy rule not found.")
    get_audit_service().record_event(
        current_user.id,
        "POLICY_RULE_RETIRED",
        f"policy_rule:{rule_id}",
        {"scheme_id": record["scheme_id"], "rule_key": record["rule_key"], "reason": body.retirement_reason},
    )
    return record


@router.post("/schemes/{scheme_id}/evaluate", status_code=status.HTTP_200_OK)
def evaluate_scheme_eligibility(
    scheme_id: str,
    body: PolicyEvaluationRequest,
    current_user: AuthenticatedUser = Depends(require_roles(*_ALL_ROLES)),
) -> Dict[str, Any]:
    repo = PostgresPolicyRuleRepository()
    candidates = repo.get_applicable_rules(scheme_id, body.rule_key, body.as_of)
    if len(candidates) != 1:
        outcome = "UNKNOWN"
        status_value = "RULE_UNAVAILABLE"
        trace: Dict[str, Any] = {
            "evidence_gate": "No unique approved and effective policy rule version is available.",
            "rule_trace": None,
            "source_references": [],
            "facts": {},
        }
        selected = None
    else:
        selected = candidates[0]
        requirement_map = selected.get("evidence_requirements") or {}
        expected_facts = set(requirement_map)
        supplied_facts = set(body.fact_quantity_ids)
        issues: List[Dict[str, str]] = []
        if supplied_facts != expected_facts:
            for fact in sorted(expected_facts - supplied_facts):
                issues.append({"fact": fact, "reason": "quantity ID mapping is missing"})
            for fact in sorted(supplied_facts - expected_facts):
                issues.append({"fact": fact, "reason": "quantity ID does not correspond to a rule predicate"})

        quantities: Dict[str, Any] = {}
        source_repo = PostgresSourceRepository()
        quantity_repo = PostgresQuantityRepository()
        for fact in sorted(expected_facts & supplied_facts):
            quantity_id = body.fact_quantity_ids[fact]
            quantity = quantity_repo.get(quantity_id)
            requirement = requirement_map[fact]
            if quantity is None:
                issues.append({"fact": fact, "reason": "ledger quantity ID is not registered"})
                continue
            if quantity.definition_key != requirement.get("definition_key"):
                issues.append({"fact": fact, "reason": "ledger definition does not match the approved evidence requirement"})
            if quantity.unit != requirement.get("unit"):
                issues.append({"fact": fact, "reason": "ledger unit does not match the approved evidence requirement"})
            if quantity.kind.value not in requirement.get("allowed_kinds", []):
                issues.append({"fact": fact, "reason": "ledger evidence kind is not allowed by the approved rule"})
            if quantity.evidence_floor < int(requirement.get("minimum_evidence_floor", 4)):
                issues.append({"fact": fact, "reason": "ledger evidence floor is below the approved rule requirement"})
            if quantity.owner_id not in (None, current_user.id):
                issues.append({"fact": fact, "reason": "ledger quantity belongs to another user"})
            quantity_date = date.fromisoformat(quantity.as_of) if quantity.as_of else None
            if quantity_date is None or quantity_date > body.as_of:
                issues.append({"fact": fact, "reason": "ledger quantity is missing or later than the assessment date"})
            refs = list(quantity.source_refs or ())
            if quantity.kind in (Kind.OBSERVED, Kind.POLICY_RULE):
                if not refs:
                    issues.append({"fact": fact, "reason": "source-backed evidence has no source-version reference"})
                for source_ref in refs:
                    source_version_id = source_ref[0] if isinstance(source_ref, (tuple, list)) and source_ref else None
                    source_version = source_repo.get_version(str(source_version_id)) if source_version_id else None
                    source = source_repo.get_source(source_version["source_id"]) if source_version else None
                    if (
                        not isinstance(source_ref, (tuple, list))
                        or len(source_ref) < 2
                        or not str(source_ref[1]).strip()
                        or source_version is None
                        or source_version.get("status") != "ACTIVE"
                        or source is None
                        or source.get("status") != "ACTIVE"
                        or not source_version.get("source_url")
                        or not _HEX_SHA256.fullmatch(str(source_version.get("content_hash") or ""))
                    ):
                        issues.append({"fact": fact, "reason": "quantity references an unregistered or inactive source version"})
            quantities[fact] = quantity

        facts = {
            fact: quantity.value if fact in quantities and not any(issue["fact"] == fact for issue in issues) else None
            for fact in expected_facts
        }
        evaluator_trace = EligibilityEvaluator(facts).evaluate(parse_rule_ast(selected["rule_ast"]))
        outcome = evaluator_trace.result.value if not issues else "UNKNOWN"
        if issues:
            status_value = "INSUFFICIENT_DATA"
        elif all(
            quantities[fact].kind in (Kind.OBSERVED, Kind.POLICY_RULE)
            and quantities[fact].evidence_floor >= 4
            for fact in expected_facts
        ):
            status_value = "ASSESSED"
        else:
            status_value = "SCENARIO_ONLY"
        trace = {
            "evidence_gate": "INCOMPLETE" if issues else "PASSED",
            "evidence_issues": issues,
            "rule_trace": _trace_to_dict(evaluator_trace),
            "facts": {
                fact: {
                    "quantity_id": str(body.fact_quantity_ids[fact]),
                    "definition_key": quantities[fact].definition_key,
                    "unit": quantities[fact].unit,
                    "kind": quantities[fact].kind.value,
                    "evidence_floor": quantities[fact].evidence_floor,
                    "as_of": quantities[fact].as_of,
                    "source_refs": [list(ref) if isinstance(ref, tuple) else ref for ref in quantities[fact].source_refs],
                }
                for fact in sorted(expected_facts & supplied_facts) if fact in quantities
            },
            "source_references": selected.get("source_references", []),
        }

    evaluation_id = repo.save_evaluation({
        "owner_id": current_user.id,
        "scheme_id": scheme_id,
        "rule_id": selected["id"] if selected else None,
        "rule_key": body.rule_key,
        "rule_version": selected["version"] if selected else None,
        "as_of": body.as_of,
        "outcome": outcome,
        "status": status_value,
        "fact_quantity_ids": {fact: str(qid) for fact, qid in body.fact_quantity_ids.items()},
        "trace": trace,
    })
    get_audit_service().record_event(
        current_user.id,
        "POLICY_ELIGIBILITY_EVALUATED",
        f"policy_evaluation:{evaluation_id}",
        {"scheme_id": scheme_id, "rule_key": body.rule_key, "rule_version": selected["version"] if selected else None, "outcome": outcome, "status": status_value},
    )
    return {
        "id": evaluation_id,
        "scheme_id": scheme_id,
        "rule_key": body.rule_key,
        "rule_version": selected["version"] if selected else None,
        "as_of": body.as_of.isoformat(),
        "outcome": outcome,
        "status": status_value,
        "official_award_decision": False,
        "trace": trace,
    }


@router.get("/evaluations/{evaluation_id}")
def get_policy_evaluation(
    evaluation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_roles(*_ALL_ROLES)),
) -> Dict[str, Any]:
    record = PostgresPolicyRuleRepository().get_evaluation(evaluation_id, owner_id=current_user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Policy evaluation not found.")
    return record


def _trace_to_dict(trace: EvaluationTrace) -> Dict[str, Any]:
    return {
        "node_type": trace.node_type,
        "result": trace.result.value,
        "reason": trace.reason,
        "fact": trace.fact,
        "comparison": trace.comparison.value if trace.comparison else None,
        "observed": trace.observed,
        "expected": list(trace.expected) if isinstance(trace.expected, tuple) else trace.expected,
        "children": [_trace_to_dict(child) for child in trace.children],
    }
