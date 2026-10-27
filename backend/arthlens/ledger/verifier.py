"""
LedgerVerifier orchestration and VerificationReport.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.5, 5.1).
Phase: P1-4 (Verification Specifications, LedgerVerifier, ReportRenderer).

Properties:
- Combines the nine verification specifications (V1-V9) via an AndSpecification.
- Evaluates individual quantities, claims, or entire epistemic ledgers.
- Never silently upgrades evidence quality or bypasses failed specifications.
- Produces deterministic, inspectable verification reports.
"""

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Set, Tuple

from backend.arthlens.domain.interfaces import SpecResult, VerificationSpecification
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.specs import (
    AndSpecification,
    ContradictionVisibilitySpec,
    DerivationDowngradeSpec,
    GeographicPrecisionSpec,
    MissingAssumptionSpec,
    PolicyCitationSpec,
    ReproducibilitySpec,
    SimulationModelVersionSpec,
    SourceAttributionSpec,
    UnitCompatibilitySpec,
)


@dataclass(frozen=True)
class VerificationReport:
    """
    Structured outcome of a verification run across specifications.

    Handbook Reference: Section 4.5.
    Attributes:
        passed: True if and only if all evaluated specifications passed.
        results: Tuple of all individual SpecResult objects.
        failures: Tuple of failing SpecResult objects.
        offending_quantity_ids: Tuple of IDs of quantities that failed verification.
        summary: Human-readable diagnostic summary (for Agent Console / audit).
    """
    passed: bool
    results: Tuple[SpecResult, ...]
    failures: Tuple[SpecResult, ...]
    offending_quantity_ids: Tuple[str, ...]
    summary: str

    def __bool__(self) -> bool:
        return self.passed


class LedgerVerifier:
    """
    Verification orchestrator combining specifications to gate claims and quantities.

    Handbook Reference: Section 4.5:
        'Specifications are independent classes combined with an AndSpecification
        inside LedgerVerifier. Each returns a result object with pass/fail,
        the offending quantity id, and a human-readable reason.'
    """

    def __init__(self, specs: Optional[Sequence[VerificationSpecification]] = None) -> None:
        """
        Initialize LedgerVerifier with modular specifications.
        Defaults to the authoritative nine specifications (V1-V9).
        """
        if specs is None:
            self._specs: List[VerificationSpecification] = [
                DerivationDowngradeSpec(),
                GeographicPrecisionSpec(),
                PolicyCitationSpec(),
                SourceAttributionSpec(),
                ContradictionVisibilitySpec(),
                UnitCompatibilitySpec(),
                ReproducibilitySpec(),
                MissingAssumptionSpec(),
                SimulationModelVersionSpec(),
            ]
        else:
            self._specs = list(specs)

        self._composite = AndSpecification(*self._specs)

    @property
    def specifications(self) -> Sequence[VerificationSpecification]:
        """Return the sequence of configured specifications."""
        return tuple(self._specs)

    def verify_quantity(self, quantity: Quantity, ledger: Optional[Ledger] = None) -> VerificationReport:
        """
        Verify a single Quantity against all specifications.

        Args:
            quantity: Quantity instance to verify.
            ledger: Epistemic ledger instance providing graph context.
        """
        results: List[SpecResult] = self._composite.check_all(quantity, ledger)
        failures = [r for r in results if not r.passed]
        passed = len(failures) == 0

        offending_ids: Set[str] = set()
        for f in failures:
            if f.offending_quantity_id:
                offending_ids.add(f.offending_quantity_id)
            else:
                offending_ids.add(quantity.id)

        if passed:
            summary = f"Quantity '{quantity.id}' passed all {len(results)} verification specifications."
        else:
            reasons = "; ".join(f"{f.spec_name}: {f.reason}" for f in failures)
            summary = f"Quantity '{quantity.id}' failed {len(failures)} verification specifications: {reasons}"

        return VerificationReport(
            passed=passed,
            results=tuple(results),
            failures=tuple(failures),
            offending_quantity_ids=tuple(sorted(offending_ids)),
            summary=summary,
        )

    def verify(self, claim: Any, ledger: Optional[Ledger] = None) -> VerificationReport:
        """
        Verify a claim or quantity against the ledger state.

        Args:
            claim: Quantity, quantity_id string, or claim dict.
            ledger: Active Epistemic Ledger.
        """
        if isinstance(claim, Quantity):
            return self.verify_quantity(claim, ledger)

        if isinstance(claim, str) and ledger is not None and claim in ledger:
            return self.verify_quantity(ledger.get(claim), ledger)

        results: List[SpecResult] = self._composite.check_all(claim, ledger)
        failures = [r for r in results if not r.passed]
        passed = len(failures) == 0

        offending_ids: Set[str] = set()
        for f in failures:
            if f.offending_quantity_id:
                offending_ids.add(f.offending_quantity_id)

        if passed:
            summary = f"Claim passed all {len(results)} verification specifications."
        else:
            reasons = "; ".join(f"{f.spec_name}: {f.reason}" for f in failures)
            summary = f"Claim failed {len(failures)} verification specifications: {reasons}"

        return VerificationReport(
            passed=passed,
            results=tuple(results),
            failures=tuple(failures),
            offending_quantity_ids=tuple(sorted(offending_ids)),
            summary=summary,
        )

    def verify_ledger(self, ledger: Ledger) -> VerificationReport:
        """
        Verify all registered quantities within the ledger.

        Args:
            ledger: Active Epistemic Ledger instance.
        """
        all_results: List[SpecResult] = []
        all_failures: List[SpecResult] = []
        offending_ids: Set[str] = set()

        for quantity in ledger:
            report = self.verify_quantity(quantity, ledger)
            all_results.extend(report.results)
            if not report.passed:
                all_failures.extend(report.failures)
                offending_ids.update(report.offending_quantity_ids)

        passed = len(all_failures) == 0
        if passed:
            summary = f"All {len(ledger)} quantities in ledger passed all verification specifications."
        else:
            summary = f"Ledger verification failed: {len(all_failures)} failure(s) across {len(offending_ids)} quantity(ies)."

        return VerificationReport(
            passed=passed,
            results=tuple(all_results),
            failures=tuple(all_failures),
            offending_quantity_ids=tuple(sorted(offending_ids)),
            summary=summary,
        )

    def is_valid(self, claim_or_quantity: Any, ledger: Optional[Ledger] = None) -> bool:
        """Return True if the claim or quantity passes all specifications, False otherwise."""
        return self.verify(claim_or_quantity, ledger).passed
