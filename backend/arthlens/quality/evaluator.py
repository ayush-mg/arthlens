"""
Multi-Dimensional Data Quality Evaluator (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 7.5 Step 10, Part 10.2).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).

Evaluates quality deterministically across:
- Source and source version
- Quantity or indicator
- Geographic unit (e.g. 'in:district:120')
- Observation/reference period (as_of)

Enforces:
1. Missing indicator values are UNAVAILABLE, NEVER numeric zero.
2. A single district may have different quality statuses for different indicators.
3. All applicable secondary issues and explanations are preserved.
4. Primary display state is selected via strict precedence (UNAVAILABLE > INCOMPLETE > STALE > ESTIMATED > CURRENT).
5. Independence from navigation, geometry, and analytical availability.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Union

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.geo import GeoUnit
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.freshness import FreshnessEvaluation, evaluate_staleness
from backend.arthlens.quality.vocabulary import (
    AtlasShadingToken,
    CalculationSuitability,
    QualityIssue,
    QualityStatus,
    get_shading_token,
    resolve_primary_status,
)


@dataclass(frozen=True)
class IndicatorQualityAssessment:
    """
    Complete multidimensional quality assessment for a specific indicator and geographic unit.
    Preserves all secondary issues alongside the primary presentation state.
    """
    geo_unit_id: str
    indicator_key: str
    primary_status: QualityStatus
    shading: AtlasShadingToken
    suitability: CalculationSuitability
    value: Optional[float]
    unit: str
    kind: Optional[Kind]
    evidence_floor: Optional[int]
    as_of: Optional[str]
    source_id: Optional[str]
    source_version_id: Optional[str]
    is_stale: bool
    explanation: str
    issues: List[QualityIssue] = field(default_factory=list)
    staleness_explanation: Optional[str] = None
    freshness: Optional[FreshnessEvaluation] = None
    evaluation_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize quality assessment for Atlas UI overlay and API responses."""
        return {
            "geo_unit_id": self.geo_unit_id,
            "indicator_key": self.indicator_key,
            "primary_status": self.primary_status.value,
            "value": self.value,
            "unit": self.unit,
            "kind": self.kind.value if self.kind else None,
            "evidence_floor": self.evidence_floor,
            "as_of": self.as_of,
            "source_id": self.source_id,
            "source_version_id": self.source_version_id,
            "is_stale": self.is_stale,
            "explanation": self.explanation,
            "staleness_explanation": self.staleness_explanation,
            "suitability": self.suitability.value,
            "shading": {
                "status": self.shading.status.value,
                "label": self.shading.label,
                "color_token": self.shading.color_token,
                "hex_color": self.shading.hex_color,
                "fill_opacity": self.shading.fill_opacity,
                "stroke_style": self.shading.stroke_style,
                "pattern": self.shading.pattern,
            },
            "issues": [
                {
                    "status": i.status.value,
                    "reason": i.reason,
                    "dimension": i.dimension,
                    "severity": i.severity,
                }
                for i in self.issues
            ],
            "evaluation_date": self.evaluation_date.isoformat() if self.evaluation_date else None,
        }


class DataQualityEvaluator:
    """
    Deterministic quality evaluator implementing ArthLens P2-3 specification.
    Assesses indicators and geographic units without guessing or silent zeroes.
    """

    def __init__(self, evaluation_date: Optional[Union[str, date, datetime]] = None) -> None:
        self.evaluation_date = (
            date.fromisoformat(str(evaluation_date)[:10])
            if evaluation_date is not None
            else date.today()
        )

    def evaluate_quantity(
        self,
        quantity: Optional[Quantity],
        indicator_key: str,
        geo_unit_id: str,
        source_id: Optional[str] = None,
        source_version_id: Optional[str] = None,
        expected_subunits: Optional[Sequence[str]] = None,
        actual_subunits: Optional[Sequence[str]] = None,
        retrieval_date: Optional[Union[str, date, datetime]] = None,
        provenance_complete: Optional[bool] = None,
        source_ids: Optional[Sequence[str]] = None,
    ) -> IndicatorQualityAssessment:
        """
        Evaluate quality for a single quantity against a target geographic unit.
        """
        issues: List[QualityIssue] = []

        # 1. Missing data check (UNAVAILABLE)
        if quantity is None or quantity.value is None:
            issue = QualityIssue(
                status=QualityStatus.UNAVAILABLE,
                reason=(
                    f"Indicator '{indicator_key}' is unavailable for '{geo_unit_id}'; "
                    f"no record exists in the epistemic ledger. Never represented as numeric zero."
                ),
                dimension="presence",
                severity="BLOCKING",
            )
            issues.append(issue)
            token = get_shading_token(QualityStatus.UNAVAILABLE)
            return IndicatorQualityAssessment(
                geo_unit_id=geo_unit_id,
                indicator_key=indicator_key,
                primary_status=QualityStatus.UNAVAILABLE,
                shading=token,
                suitability=CalculationSuitability.UNSUITABLE_MISSING,
                value=None,
                unit="",
                kind=None,
                evidence_floor=None,
                as_of=None,
                source_id=source_id,
                source_version_id=source_version_id,
                is_stale=False,
                explanation=issue.reason,
                issues=issues,
                evaluation_date=self.evaluation_date,
            )

        if provenance_complete is False:
            issues.append(
                QualityIssue(
                    status=QualityStatus.INCOMPLETE,
                    reason=(
                        f"Exact source provenance could not be verified for '{indicator_key}' "
                        f"in '{geo_unit_id}'."
                    ),
                    dimension="source_provenance",
                    severity="WARNING",
                )
            )

        # 2. Geographic completeness check (INCOMPLETE)
        if quantity.geo_unit_id != geo_unit_id:
            issues.append(
                QualityIssue(
                    status=QualityStatus.INCOMPLETE,
                    reason=(
                        f"Geographic mismatch: Quantity references '{quantity.geo_unit_id}', "
                        f"but requested unit is '{geo_unit_id}'."
                    ),
                    dimension="geographic_alignment",
                    severity="WARNING",
                )
            )

        if expected_subunits and actual_subunits is not None:
            missing_subs = set(expected_subunits) - set(actual_subunits)
            if missing_subs:
                issues.append(
                    QualityIssue(
                        status=QualityStatus.INCOMPLETE,
                        reason=(
                            f"Incomplete sub-unit coverage: {len(missing_subs)} of {len(expected_subunits)} "
                            f"sub-units missing for '{geo_unit_id}'."
                        ),
                        dimension="subdistrict_coverage",
                        severity="WARNING",
                    )
                )

        # 2b. Numeric contradiction detection (CONTRADICTED)
        # Verification V5: If two sources disagree beyond tolerance, mark contradicted / disputed.
        if "CONTRADICTED" in quantity.quality_flags or "DISPUTED" in quantity.quality_flags:
            issues.append(
                QualityIssue(
                    status=QualityStatus.CONTRADICTED,
                    reason=(
                        f"Numeric contradiction detected for '{indicator_key}' in '{geo_unit_id}': "
                        f"multiple authoritative sources disagree beyond tolerance (Verification V5)."
                    ),
                    dimension="source_agreement",
                    severity="BLOCKING",
                )
            )
        if "CONTRADICTED_ANCESTRY" in quantity.quality_flags:
            issues.append(
                QualityIssue(
                    status=QualityStatus.CONTRADICTED,
                    reason=(
                        f"Ancestral contradiction detected for '{indicator_key}' in '{geo_unit_id}': "
                        f"ancestral derivation inputs contain numeric contradictions."
                    ),
                    dimension="source_agreement",
                    severity="BLOCKING",
                )
            )

        # 2c. Inherited and source completeness checks (INCOMPLETE)
        if "INCOMPLETE_SOURCE" in quantity.quality_flags:
            issues.append(
                QualityIssue(
                    status=QualityStatus.INCOMPLETE,
                    reason=(
                        f"Incomplete source data for '{indicator_key}' in '{geo_unit_id}': "
                        f"derived from incomplete source records or partial attributes."
                    ),
                    dimension="source_completeness",
                    severity="WARNING",
                )
            )
        if "LOW_COVERAGE" in quantity.quality_flags:
            issues.append(
                QualityIssue(
                    status=QualityStatus.INCOMPLETE,
                    reason=(
                        f"Low sub-unit spatial coverage detected for '{indicator_key}' in '{geo_unit_id}'."
                    ),
                    dimension="spatial_coverage",
                    severity="WARNING",
                )
            )

        # 3. Observation freshness / staleness evaluation (STALE)
        # A source-version citation is not itself a source ID. Resolve exact
        # version records at the repository boundary and pass their registered
        # source IDs explicitly; bare or legacy source_refs never select policy.
        src_id = source_id.strip() if isinstance(source_id, str) and source_id.strip() else None
        resolved_source_ids = tuple(
            dict.fromkeys(
                value.strip()
                for value in (source_ids or ((src_id,) if src_id else ()))
                if isinstance(value, str) and value.strip()
            )
        )
        if src_id is None and resolved_source_ids:
            src_id = resolved_source_ids[0]
        freshness_results = [
            evaluate_staleness(
                as_of=quantity.as_of,
                source_id=resolved_id,
                evaluation_date=self.evaluation_date,
                retrieval_date=retrieval_date,
            )
            for resolved_id in resolved_source_ids
        ]
        if not freshness_results:
            freshness_results = [
                evaluate_staleness(
                    as_of=quantity.as_of,
                    evaluation_date=self.evaluation_date,
                    retrieval_date=retrieval_date,
                )
            ]
        freshness = freshness_results[0]
        is_source_stale = any(result.is_stale for result in freshness_results)
        all_sources_have_policy = all(result.has_policy for result in freshness_results)
        if len(freshness_results) > 1:
            freshness = replace(
                freshness,
                is_stale=is_source_stale,
                max_age_days=None,
                has_policy=all_sources_have_policy,
                explanation=" ".join(result.explanation for result in freshness_results),
            )
        elif is_source_stale != freshness.is_stale:
            freshness = replace(freshness, is_stale=is_source_stale)

        is_estimated = (quantity.kind == Kind.ESTIMATED or "SYNTHETIC_DATA" in quantity.quality_flags)
        if is_estimated:
            issues.append(
                QualityIssue(
                    status=QualityStatus.ESTIMATED,
                    reason=(
                        f"Value is modelled / estimated (kind={quantity.kind.value}), "
                        f"not an empirical direct observation."
                    ),
                    dimension="epistemic_kind",
                    severity="INFO",
                )
            )

        staleness_explanation: Optional[str] = None
        if not quantity.as_of or freshness.as_of_date is None:
            if not is_estimated:
                issues.append(
                    QualityIssue(
                        status=QualityStatus.INCOMPLETE,
                        reason=f"Observation date (as_of) is missing or invalid ('{quantity.as_of}'); freshness cannot be certified as CURRENT.",
                        dimension="temporal_freshness",
                        severity="WARNING",
                    )
                )
        elif is_source_stale or "STALE" in quantity.quality_flags or "STALE_ANCESTRY" in quantity.quality_flags:
            if is_source_stale:
                staleness_explanation = freshness.explanation
            elif "STALE_ANCESTRY" in quantity.quality_flags:
                staleness_explanation = "Inherited staleness: one or more ancestral calculation inputs are stale (STALE_ANCESTRY)."
            else:
                staleness_explanation = "Observation period exceeds approved source freshness threshold."
            issues.append(
                QualityIssue(
                    status=QualityStatus.STALE,
                    reason=staleness_explanation,
                    dimension="temporal_freshness",
                    severity="WARNING",
                )
            )
        elif not all_sources_have_policy and not is_estimated:
            # Source lacks an approved freshness policy: never label empirical evidence CURRENT solely because no threshold exists!
            issues.append(
                QualityIssue(
                    status=QualityStatus.INCOMPLETE,
                    reason=(
                        f"Source '{src_id}' lacks an approved freshness policy. "
                        f"Freshness is unverified; evidence cannot be certified as CURRENT."
                    ),
                    dimension="temporal_freshness",
                    severity="WARNING",
                )
            )

        # 5. If no issues were detected, observation is fresh, complete, and observed (CURRENT)
        if not issues:
            issues.append(
                QualityIssue(
                    status=QualityStatus.CURRENT,
                    reason=(
                        f"Observation date {quantity.as_of} is current and complete "
                        f"for '{geo_unit_id}' (as of {self.evaluation_date.isoformat()})."
                    ),
                    dimension="temporal_freshness",
                    severity="INFO",
                )
            )

        # Determine primary display status using strict deterministic precedence
        primary_status = resolve_primary_status([i.status for i in issues])
        token = get_shading_token(primary_status)

        # Map suitability
        suitability_map = {
            QualityStatus.CURRENT: CalculationSuitability.SUITABLE_CURRENT,
            QualityStatus.INCOMPLETE: CalculationSuitability.CAUTION_PARTIAL,
            QualityStatus.STALE: CalculationSuitability.SUITABLE_HISTORICAL_ONLY,
            QualityStatus.ESTIMATED: CalculationSuitability.ESTIMATED_PROJECTION,
            QualityStatus.UNAVAILABLE: CalculationSuitability.UNSUITABLE_MISSING,
            QualityStatus.CONTRADICTED: CalculationSuitability.UNSUITABLE_CONTRADICTED,
        }
        suitability = suitability_map[primary_status]

        # Primary explanation from highest precedence issue
        primary_issue = next((i for i in issues if i.status == primary_status), issues[0])

        return IndicatorQualityAssessment(
            geo_unit_id=geo_unit_id,
            indicator_key=indicator_key,
            primary_status=primary_status,
            shading=token,
            suitability=suitability,
            value=quantity.value,
            unit=quantity.unit,
            kind=quantity.kind,
            evidence_floor=quantity.evidence_floor,
            as_of=quantity.as_of,
            source_id=src_id,
            source_version_id=source_version_id,
            is_stale=is_source_stale or "STALE" in quantity.quality_flags or "STALE_ANCESTRY" in quantity.quality_flags,
            explanation=primary_issue.reason,
            issues=issues,
            staleness_explanation=staleness_explanation,
            freshness=freshness,
            evaluation_date=self.evaluation_date,
        )

    def evaluate_geo_unit_indicators(
        self,
        geo_unit: GeoUnit,
        quantities: Sequence[Quantity],
        target_indicators: Sequence[str],
    ) -> Dict[str, IndicatorQualityAssessment]:
        """
        Evaluate a complete suite of indicators for a geographic unit.
        Demonstrates that a single district can hold different quality statuses across different indicators.
        """
        results: Dict[str, IndicatorQualityAssessment] = {}
        q_by_key = {q.definition_key: q for q in quantities if q.geo_unit_id == geo_unit.id}

        for ind_key in target_indicators:
            q = q_by_key.get(ind_key)
            results[ind_key] = self.evaluate_quantity(
                quantity=q,
                indicator_key=ind_key,
                geo_unit_id=geo_unit.id,
            )

        return results
