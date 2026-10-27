"""
The Nine Modular Verification Specifications and AndSpecification.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.5, 5.1, 5.2).
Phase: P1-4 (Verification Specifications, LedgerVerifier, ReportRenderer).

Contains:
- SpecResult: Result object with pass/fail, offending quantity id, and human-readable reason.
- AndSpecification: Specification pattern composite combining multiple specifications.
- V1: DerivationDowngradeSpec
- V2: GeographicPrecisionSpec
- V3: PolicyCitationSpec
- V4: SourceAttributionSpec
- V5: ContradictionVisibilitySpec
- V6: UnitCompatibilitySpec
- V7: ReproducibilitySpec
- V8: MissingAssumptionSpec
- V9: SimulationModelVersionSpec
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.interfaces import SpecResult, VerificationSpecification
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.simulation import SimulationMetadata
from backend.arthlens.ledger.downscaling import DownscalingRegistry
from backend.arthlens.ledger.propagation import combine_evidence_floors
from backend.arthlens.ledger.staleness import parse_as_of_date
from backend.arthlens.ledger.units import check_unit_compatibility, get_unit_registry


def _resolve_quantity(claim: Any, ledger: Any) -> Optional[Quantity]:
    """Helper to extract a Quantity object from a claim or quantity id."""
    if isinstance(claim, Quantity):
        return claim
    if isinstance(claim, str) and ledger is not None:
        try:
            return ledger.get(claim)
        except (KeyError, TypeError):
            return None
    if isinstance(claim, dict):
        if "quantity" in claim and isinstance(claim["quantity"], Quantity):
            return claim["quantity"]
        if "quantity_id" in claim and ledger is not None:
            try:
                return ledger.get(claim["quantity_id"])
            except (KeyError, TypeError):
                return None
    return None


class AndSpecification(VerificationSpecification):
    """
    Specification composite executing all child specifications using logical AND.

    Handbook Reference: Section 4.5, 5.2:
        'Specifications are independent classes combined with an AndSpecification
        inside LedgerVerifier. Each returns a result object with pass/fail,
        the offending quantity id, and a human-readable reason.'
    """

    def __init__(self, *specs: VerificationSpecification) -> None:
        self.specs: List[VerificationSpecification] = list(specs)

    def add(self, spec: VerificationSpecification) -> "AndSpecification":
        """Add a child specification to the composite chain."""
        self.specs.append(spec)
        return self

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        """
        Evaluate all child specifications sequentially.
        Fails on the first failing specification.
        """
        for spec in self.specs:
            result = spec.check(claim, ledger)
            if not result.passed:
                return result
        return SpecResult(
            passed=True,
            spec_name="AndSpecification",
            reason="All child specifications passed.",
        )

    def check_all(self, claim: Any, ledger: Any) -> List[SpecResult]:
        """Evaluate all child specifications and return results for all of them."""
        return [spec.check(claim, ledger) for spec in self.specs]


class DerivationDowngradeSpec(VerificationSpecification):
    """
    V1: DerivationDowngradeSpec

    Handbook Reference: Section 4.5:
        'A derived value is never labelled OBSERVED; the described class must not
        be stronger than the computed floor.'
    """

    SPEC_NAME = "V1_DerivationDowngradeSpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        is_derived = len(q.parent_ids) > 0 or q.kind in (Kind.CALCULATED, Kind.SIMULATED)

        # Rule 1: A derived quantity is never labelled OBSERVED
        if is_derived and q.kind == Kind.OBSERVED:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                offending_quantity_id=q.id,
                reason=(
                    f"Derived quantity '{q.id}' has {len(q.parent_ids)} parents "
                    f"but is labelled OBSERVED (Handbook 4.2, 4.5)."
                ),
                details={"kind": q.kind.value, "parent_count": len(q.parent_ids)},
            )

        # Rule 2: Evidence floor must not be stronger than computed floor of parents
        if q.parent_ids and ledger is not None:
            parent_floors = [
                ledger.get(pid).evidence_floor
                for pid in q.parent_ids
                if pid in ledger
            ]
            if parent_floors:
                min_parent_floor = min(parent_floors)
                parent_resolutions = [
                    ledger.get(pid).resolution
                    for pid in q.parent_ids
                    if pid in ledger
                ]
                is_downscaling = (
                    bool(parent_resolutions)
                    and q.resolution > min(parent_resolutions)
                    and DownscalingRegistry.is_registered(q.method_id)
                )
                max_allowed_floor = min(min_parent_floor, 2) if is_downscaling else min_parent_floor

                if q.evidence_floor > max_allowed_floor:
                    return SpecResult(
                        passed=False,
                        spec_name=self.SPEC_NAME,
                        offending_quantity_id=q.id,
                        reason=(
                            f"Quantity '{q.id}' declares evidence floor {q.evidence_floor}, "
                            f"which is stronger than the computed floor {max_allowed_floor} "
                            f"of its weakest parent (Handbook 4.2)."
                        ),
                        details={
                            "declared_floor": q.evidence_floor,
                            "max_allowed_floor": max_allowed_floor,
                        },
                    )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


class GeographicPrecisionSpec(VerificationSpecification):
    """
    V2: GeographicPrecisionSpec

    Handbook Reference: Section 4.5:
        'A claim's geography must not be finer than the evidence resolution
        unless a registered downscaling method applies.'
    """

    SPEC_NAME = "V2_GeographicPrecisionSpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        if q.parent_ids and ledger is not None:
            parent_resolutions = [
                ledger.get(pid).resolution
                for pid in q.parent_ids
                if pid in ledger
            ]
            if parent_resolutions:
                coarsest = min(parent_resolutions)
                if q.resolution > coarsest:
                    # Spatial resolution refines beyond coarsest parent
                    if not DownscalingRegistry.is_registered(q.method_id):
                        return SpecResult(
                            passed=False,
                            spec_name=self.SPEC_NAME,
                            offending_quantity_id=q.id,
                            reason=(
                                f"Quantity '{q.id}' resolution {q.resolution} is finer than "
                                f"coarsest parent resolution {coarsest} without a registered "
                                f"downscaling method (Handbook 4.3). Method '{q.method_id}' is not registered."
                            ),
                            details={
                                "declared_resolution": q.resolution,
                                "coarsest_parent_resolution": coarsest,
                                "method_id": q.method_id,
                            },
                        )

                    # When registered downscaling applies, output must be ESTIMATED and floor <= 2
                    if q.kind != Kind.ESTIMATED:
                        return SpecResult(
                            passed=False,
                            spec_name=self.SPEC_NAME,
                            offending_quantity_id=q.id,
                            reason=(
                                f"Downscaled quantity '{q.id}' must have kind ESTIMATED, "
                                f"got {q.kind.value} (Handbook 4.3)."
                            ),
                        )
                    if q.evidence_floor > 2:
                        return SpecResult(
                            passed=False,
                            spec_name=self.SPEC_NAME,
                            offending_quantity_id=q.id,
                            reason=(
                                f"Downscaled quantity '{q.id}' must have evidence_floor at most 2, "
                                f"got {q.evidence_floor} (Handbook 4.3)."
                            ),
                        )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


class PolicyCitationSpec(VerificationSpecification):
    """
    V3: PolicyCitationSpec

    Handbook Reference: Section 4.5, 4.7:
        'A policy claim must cite a POLICY_RULE record whose version was valid on
        the stated date.'
        'Policy: a rule not valid on the as-of date is rejected by V3.'
    """

    SPEC_NAME = "V3_PolicyCitationSpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)

        # Check if claim is directly a POLICY_RULE or references a POLICY_RULE
        policy_quantities = []
        target_date_str = None

        if q is not None:
            target_date_str = q.as_of
            if q.kind == Kind.POLICY_RULE:
                policy_quantities.append(q)
            elif ledger is not None and q.parent_ids:
                for pid in q.parent_ids:
                    if pid in ledger:
                        parent_q = ledger.get(pid)
                        if parent_q.kind == Kind.POLICY_RULE:
                            policy_quantities.append(parent_q)

        # Check if claim is a dict asserting policy compliance
        if isinstance(claim, dict):
            if "rule_id" in claim and ledger is not None and claim["rule_id"] in ledger:
                policy_quantities.append(ledger.get(claim["rule_id"]))
            if "as_of" in claim:
                target_date_str = claim["as_of"]

        # If no policy rules are involved in this claim, it passes V3
        if not policy_quantities:
            return SpecResult(passed=True, spec_name=self.SPEC_NAME)

        for rule_q in policy_quantities:
            # Rule must cite an authoritative policy document
            if not rule_q.source_refs:
                return SpecResult(
                    passed=False,
                    spec_name=self.SPEC_NAME,
                    offending_quantity_id=rule_q.id,
                    reason=f"Policy rule '{rule_q.id}' must cite an official policy document in source_refs.",
                )

            # Check temporal validity on stated date
            if target_date_str:
                try:
                    eval_date = parse_as_of_date(target_date_str)
                except Exception:
                    eval_date = None

                if eval_date:
                    # Look for validity window in source_refs or license_meta
                    # Format: (version_id, locator, retrieval_date, valid_from, valid_to) or dict in source_refs
                    for ref in rule_q.source_refs:
                        valid_from = None
                        valid_to = None
                        if isinstance(ref, dict):
                            valid_from = ref.get("valid_from")
                            valid_to = ref.get("valid_to")
                        elif isinstance(ref, (list, tuple)) and len(ref) >= 5:
                            valid_from = ref[3]
                            valid_to = ref[4]

                        if valid_from:
                            from_dt = parse_as_of_date(valid_from)
                            if eval_date < from_dt:
                                return SpecResult(
                                    passed=False,
                                    spec_name=self.SPEC_NAME,
                                    offending_quantity_id=rule_q.id,
                                    reason=(
                                        f"Policy rule '{rule_q.id}' version was not yet valid on {eval_date} "
                                        f"(valid from {from_dt}) (Handbook 4.5 V3)."
                                    ),
                                    details={"as_of": str(eval_date), "valid_from": str(from_dt)},
                                )
                        if valid_to:
                            to_dt = parse_as_of_date(valid_to)
                            if eval_date > to_dt:
                                return SpecResult(
                                    passed=False,
                                    spec_name=self.SPEC_NAME,
                                    offending_quantity_id=rule_q.id,
                                    reason=(
                                        f"Policy rule '{rule_q.id}' version expired on {to_dt} "
                                        f"and was not valid on stated date {eval_date} (Handbook 4.5 V3)."
                                    ),
                                    details={"as_of": str(eval_date), "valid_to": str(to_dt)},
                                )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


class SourceAttributionSpec(VerificationSpecification):
    """
    V4: SourceAttributionSpec

    Handbook Reference: Section 4.5:
        'Every number in the output is a ledger quantity with at least one source
        reference or parent chain ending in sources. Numbers found in a document
        passage must first be ingested as ledger records with a passage locator.'
    """

    SPEC_NAME = "V4_SourceAttributionSpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        # Base quantities must cite source references directly
        if not q.parent_ids:
            if not q.source_refs:
                return SpecResult(
                    passed=False,
                    spec_name=self.SPEC_NAME,
                    offending_quantity_id=q.id,
                    reason=(
                        f"Base quantity '{q.id}' (kind {q.kind.value}) has no source references "
                        "(Handbook 4.5 V4)."
                    ),
                )
            if q.kind == Kind.OBSERVED:
                # Must specify a locator
                has_locator = False
                for s in q.source_refs:
                    if isinstance(s, (tuple, list)) and len(s) >= 2 and str(s[1]).strip():
                        has_locator = True
                        break
                    elif isinstance(s, dict) and str(s.get("locator", "")).strip():
                        has_locator = True
                        break
                    elif isinstance(s, str) and s.strip():
                        has_locator = True
                        break
                if not has_locator:
                    return SpecResult(
                        passed=False,
                        spec_name=self.SPEC_NAME,
                        offending_quantity_id=q.id,
                        reason=f"OBSERVED quantity '{q.id}' must include a passage/dataset locator in source_refs.",
                    )
            return SpecResult(passed=True, spec_name=self.SPEC_NAME)

        # Derived quantities: parent chain must terminate in source-attributed roots
        if ledger is not None:
            ancestor_ids: Set[str] = set()
            queue = list(q.parent_ids)
            while queue:
                pid = queue.pop(0)
                if pid not in ancestor_ids:
                    ancestor_ids.add(pid)
                    if pid in ledger:
                        for grand_p in ledger.get(pid).parent_ids:
                            if grand_p not in ancestor_ids:
                                queue.append(grand_p)

            root_ancestor_ids = [
                aid for aid in ancestor_ids
                if aid in ledger and len(ledger.get(aid).parent_ids) == 0
            ]
            if not root_ancestor_ids:
                return SpecResult(
                    passed=False,
                    spec_name=self.SPEC_NAME,
                    offending_quantity_id=q.id,
                    reason=f"Derived quantity '{q.id}' does not trace back to any root source quantities.",
                )
            for root_id in root_ancestor_ids:
                root_q = ledger.get(root_id)
                if not root_q.source_refs:
                    return SpecResult(
                        passed=False,
                        spec_name=self.SPEC_NAME,
                        offending_quantity_id=q.id,
                        reason=(
                            f"Derived quantity '{q.id}' traces back to root ancestor '{root_id}' "
                            "which lacks source attribution."
                        ),
                    )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


class ContradictionVisibilitySpec(VerificationSpecification):
    """
    V5: ContradictionVisibilitySpec

    Handbook Reference: Section 4.5:
        'If two sources disagree beyond tolerance on the same definition,
        geography and period, both stay visible and the claim is marked disputed
        until an explicit resolution method is applied.'
    """

    SPEC_NAME = "V5_ContradictionVisibilitySpec"

    def __init__(self, tolerance: float = 0.01) -> None:
        self.tolerance = tolerance

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        if ledger is not None:
            for other in ledger:
                if (
                    other.id != q.id
                    and other.definition_key == q.definition_key
                    and other.geo_unit_id == q.geo_unit_id
                    and other.as_of == q.as_of
                    and other.source_refs != q.source_refs
                ):
                    # Check relative difference beyond tolerance
                    denom = max(abs(q.value), 1e-9)
                    rel_diff = abs(other.value - q.value) / denom

                    if rel_diff > self.tolerance:
                        # Contradiction detected
                        is_disputed = "DISPUTED" in q.quality_flags and "DISPUTED" in other.quality_flags
                        is_reconciled = (
                            bool(q.method_id and "reconciliation" in q.method_id.lower())
                            or "RECONCILED" in q.quality_flags
                        )

                        if not is_disputed and not is_reconciled:
                            return SpecResult(
                                passed=False,
                                spec_name=self.SPEC_NAME,
                                offending_quantity_id=q.id,
                                reason=(
                                    f"Contradiction detected: quantity '{q.id}' (value {q.value}) and '{other.id}' "
                                    f"(value {other.value}) disagree by {rel_diff:.1%} on definition '{q.definition_key}' "
                                    f"for geography '{q.geo_unit_id}' and period '{q.as_of}'. Both must remain visible "
                                    "and be marked DISPUTED until an explicit resolution method is applied (Handbook 4.5 V5)."
                                ),
                                details={
                                    "quantity_id": q.id,
                                    "conflicting_id": other.id,
                                    "relative_diff": rel_diff,
                                },
                            )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


class UnitCompatibilitySpec(VerificationSpecification):
    """
    V6: UnitCompatibilitySpec

    Handbook Reference: Section 4.5:
        'Operations require compatible Pint units.'
    """

    SPEC_NAME = "V6_UnitCompatibilitySpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        ureg = get_unit_registry()

        # Validate own unit expression
        try:
            ureg.parse_units(q.unit)
        except Exception as e:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                offending_quantity_id=q.id,
                reason=f"Quantity '{q.id}' has invalid Pint unit expression '{q.unit}': {e}",
            )

        # Check operation unit compatibility with parents
        if q.parent_ids and ledger is not None:
            parent_units = [
                ledger.get(pid).unit
                for pid in q.parent_ids
                if pid in ledger
            ]
            if parent_units:
                op = "add"  # Default linear/additive check
                if q.method_id in ("multiply", "divide", "add", "subtract"):
                    op = q.method_id

                try:
                    check_unit_compatibility(op, parent_units)
                except Exception as e:
                    return SpecResult(
                        passed=False,
                        spec_name=self.SPEC_NAME,
                        offending_quantity_id=q.id,
                        reason=f"Unit compatibility failure for quantity '{q.id}' under operation '{op}': {e}",
                        details={"parent_units": parent_units, "operation": op},
                    )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


def _extract_simulation_metadata(q: Any) -> Tuple[Optional[SimulationMetadata], List[str]]:
    """
    Extract and validate SimulationMetadata from a Quantity unambiguously.

    Primary path: Dedicated, typed `simulation_meta` attribute on Quantity domain model.
    Backwards compatibility: If legacy parameters in `method_id` are provided, validate and parse them.
    """
    errors: List[str] = []

    # 1. Primary path: Dedicated typed attribute on Quantity
    sim_meta = getattr(q, "simulation_meta", None)
    if sim_meta is not None:
        if isinstance(sim_meta, SimulationMetadata):
            return (sim_meta, [])
        return (None, [f"simulation_meta is invalid type: {type(sim_meta).__name__}"])

    # 2. Structured fallback parsing from legacy method_id string encoding
    scenario_id: Optional[str] = None
    model_version: Optional[str] = None
    seed_val: Optional[int] = None
    n_val: Optional[int] = None
    data_versions_list: List[str] = []

    # Model version
    if hasattr(q, "model_version") and q.model_version and q.model_version.strip():
        model_version = q.model_version.strip()
    else:
        errors.append("model_version is missing or empty")

    # Scenario ID
    method_id_str = getattr(q, "method_id", "") or ""
    def_key = getattr(q, "definition_key", "") or ""

    scen_match = re.search(r"\bscenario(?:_id)?\s*=\s*([a-zA-Z0-9_\-\.]+)\b", method_id_str, re.IGNORECASE)
    if scen_match:
        scenario_id = scen_match.group(1).strip()
    elif def_key:
        m_def = re.match(r"^(?:scenario[._-]([a-zA-Z0-9_\-]+)|([a-zA-Z0-9_\-]+)[._-]scenario)", def_key, re.IGNORECASE)
        if m_def:
            scenario_id = m_def.group(1) or m_def.group(2)
        elif "scenario" in def_key.lower():
            tokens = [t for t in re.split(r"[._-]", def_key) if "scenario" in t.lower()]
            if tokens:
                scenario_id = tokens[0]

    if not scenario_id:
        errors.append("scenario_id is missing or cannot be resolved")

    # Seed
    seed_match = re.search(r"(?:^|[\W_])seed\s*=\s*([^_\s,;]+)", method_id_str, re.IGNORECASE)
    if seed_match:
        raw_seed = seed_match.group(1).strip()
        try:
            seed_val = int(raw_seed)
            if seed_val < 0:
                errors.append(f"Invalid seed '{seed_val}': must be non-negative (>= 0)")
                seed_val = None
        except ValueError:
            errors.append(f"Malformed seed '{raw_seed}': must be an integer")
    else:
        if hasattr(q, "source_refs"):
            for s in q.source_refs:
                if isinstance(s, tuple) and len(s) >= 2 and str(s[0]).lower() == "seed":
                    try:
                        seed_val = int(s[1])
                        if seed_val < 0:
                            errors.append(f"Invalid seed '{seed_val}': must be non-negative (>= 0)")
                            seed_val = None
                    except (ValueError, TypeError):
                        errors.append(f"Malformed seed '{s[1]}': must be an integer")
                    break

    if seed_val is None and not any("seed" in e for e in errors):
        errors.append("seed is missing")

    # Sample count (N)
    n_match = re.search(r"(?:^|[\W_])(?:N|n_samples|sample_count|samples)\s*=\s*([^_\s,;]+)", method_id_str)
    if n_match:
        raw_n = n_match.group(1).strip()
        try:
            n_val = int(raw_n)
            if n_val <= 0:
                errors.append(f"Invalid sample count N '{n_val}': must be positive (> 0)")
                n_val = None
        except ValueError:
            errors.append(f"Malformed sample count N '{raw_n}': must be an integer")
    else:
        if hasattr(q, "source_refs"):
            for s in q.source_refs:
                if isinstance(s, tuple) and len(s) >= 2 and str(s[0]).lower() in ("n", "n_samples", "sample_count"):
                    try:
                        n_val = int(s[1])
                        if n_val <= 0:
                            errors.append(f"Invalid sample count N '{n_val}': must be positive (> 0)")
                            n_val = None
                    except (ValueError, TypeError):
                        errors.append(f"Malformed sample count N '{s[1]}': must be an integer")
                    break

    if n_val is None and not any("N" in e or "sample count" in e for e in errors):
        errors.append("sample count N is missing")

    # Data versions
    if hasattr(q, "source_refs") and q.source_refs:
        for s in q.source_refs:
            if isinstance(s, str) and s.strip():
                data_versions_list.append(s.strip())
            elif isinstance(s, (tuple, list)) and len(s) > 0 and isinstance(s[0], str) and s[0].strip():
                data_versions_list.append(s[0].strip())

    if not data_versions_list:
        dv_match = re.search(r"\bdata_v(?:ersions?)?\s*=\s*([^_\s,;]+)", method_id_str)
        if dv_match:
            data_versions_list.append(dv_match.group(1).strip())

    if not data_versions_list:
        errors.append("data_versions is missing")

    if errors:
        return (None, errors)

    try:
        meta = SimulationMetadata(
            scenario_id=scenario_id,  # type: ignore
            model_version=model_version,  # type: ignore
            seed=seed_val,  # type: ignore
            sample_count=n_val,  # type: ignore
            data_versions=tuple(data_versions_list),
        )
        return (meta, [])
    except (ValueError, TypeError) as e:
        return (None, [str(e)])


class ReproducibilitySpec(VerificationSpecification):
    """
    V7: ReproducibilitySpec

    Handbook Reference: Section 4.5, 4.7:
        'Calculated and simulated quantities store method, versions, seed and
        parent ids sufficient to recompute.'
    """

    SPEC_NAME = "V7_ReproducibilitySpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        if q.kind in (Kind.CALCULATED, Kind.SIMULATED):
            missing = []
            if not q.method_id or not q.method_id.strip():
                missing.append("method_id")
            if not q.model_version or not q.model_version.strip():
                missing.append("model_version")
            if not q.parent_ids:
                missing.append("parent_ids")

            if missing:
                return SpecResult(
                    passed=False,
                    spec_name=self.SPEC_NAME,
                    offending_quantity_id=q.id,
                    reason=(
                        f"Derived quantity '{q.id}' (kind {q.kind.value}) is missing reproducibility "
                        f"fields required to recompute: {', '.join(missing)} (Handbook 4.5 V7)."
                    ),
                    details={"missing_fields": missing},
                )

            # For SIMULATED quantities, V7 additionally requires valid seed and simulation parameters
            if q.kind == Kind.SIMULATED:
                meta, errors = _extract_simulation_metadata(q)
                if meta is None or errors:
                    return SpecResult(
                        passed=False,
                        spec_name=self.SPEC_NAME,
                        offending_quantity_id=q.id,
                        reason=(
                            f"Simulated quantity '{q.id}' lacks valid reproducibility metadata "
                            f"(seed/versions required to recompute): {'; '.join(errors)} (Handbook 4.5 V7)."
                        ),
                        details={"reproducibility_errors": errors},
                    )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


class MissingAssumptionSpec(VerificationSpecification):
    """
    V8: MissingAssumptionSpec

    Handbook Reference: Section 4.5:
        'No default or invented assumption: a missing required input is either
        asked of the user or filled by a registered, labelled prior (kind SCENARIO).'
    """

    SPEC_NAME = "V8_MissingAssumptionSpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        # If a quantity has no parents and no source references, it cannot masquerade as OBSERVED or CALCULATED
        if not q.parent_ids and not q.source_refs:
            if q.kind not in (Kind.USER_ASSUMED, Kind.SCENARIO):
                return SpecResult(
                    passed=False,
                    spec_name=self.SPEC_NAME,
                    offending_quantity_id=q.id,
                    reason=(
                        f"Quantity '{q.id}' has no sources or parents and is ungrounded. "
                        f"Assumptions must be asked of the user (USER_ASSUMED) or explicitly "
                        f"filled by a registered prior (SCENARIO), not labelled {q.kind.value} (Handbook 4.5 V8)."
                    ),
                )

        # For derived quantities, any ungrounded parent must be USER_ASSUMED or SCENARIO
        if q.parent_ids and ledger is not None:
            for pid in q.parent_ids:
                if pid in ledger:
                    parent_q = ledger.get(pid)
                    if not parent_q.parent_ids and not parent_q.source_refs:
                        if parent_q.kind not in (Kind.USER_ASSUMED, Kind.SCENARIO):
                            return SpecResult(
                                passed=False,
                                spec_name=self.SPEC_NAME,
                                offending_quantity_id=q.id,
                                reason=(
                                    f"Calculation '{q.id}' relies on ungrounded assumption parent '{pid}' "
                                    f"which is neither USER_ASSUMED nor SCENARIO (Handbook 4.5 V8)."
                                ),
                            )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


class SimulationModelVersionSpec(VerificationSpecification):
    """
    V9: SimulationModelVersionSpec

    Handbook Reference: Section 4.5:
        'Every simulation result names scenario id, model version, seed, N and
        data versions.'
    """

    SPEC_NAME = "V9_SimulationModelVersionSpec"

    def check(self, claim: Any, ledger: Any) -> SpecResult:
        q = _resolve_quantity(claim, ledger)
        if q is None:
            return SpecResult(
                passed=False,
                spec_name=self.SPEC_NAME,
                reason="Cannot resolve claim to a valid Quantity instance.",
            )

        if q.kind == Kind.SIMULATED:
            meta, errors = _extract_simulation_metadata(q)
            if meta is None or errors:
                return SpecResult(
                    passed=False,
                    spec_name=self.SPEC_NAME,
                    offending_quantity_id=q.id,
                    reason=(
                        f"Simulation quantity '{q.id}' is missing mandatory simulation metadata: "
                        f"{', '.join(errors)} (Handbook 4.5 V9)."
                    ),
                    details={"missing_metadata": errors},
                )

        return SpecResult(passed=True, spec_name=self.SPEC_NAME)


__all__ = [
    "SpecResult",
    "VerificationSpecification",
    "AndSpecification",
    "SimulationMetadata",
    "DerivationDowngradeSpec",
    "GeographicPrecisionSpec",
    "PolicyCitationSpec",
    "SourceAttributionSpec",
    "ContradictionVisibilitySpec",
    "UnitCompatibilitySpec",
    "ReproducibilitySpec",
    "MissingAssumptionSpec",
    "SimulationModelVersionSpec",
]
