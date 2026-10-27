"""
ReportRenderer and Free-Number Scanner (Rule G4: Ledger-Only Rendering).

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.6, 4.7).
Phase: P1-4 (Verification Specifications, LedgerVerifier, ReportRenderer).

Properties:
- The LLM writes prose containing placeholders such as {{q:UUID}}.
- The renderer substitutes each placeholder with formatted value, unit, and clickable chip.
- A scanner rejects any numeric literal not on an allowlist (section numbers,
  years that appear in a ledger quantity's period, list indices).
- Quoted source passages with locators are preserved without treating numbers as results.
- Prevents unsupported numerical claims from bypassing verification.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, FrozenSet, List, Optional, Pattern, Set, Tuple

from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.verifier import LedgerVerifier


@dataclass(frozen=True)
class AllowlistConfig:
    """
    Configuration of allowed numeric literals in rendered text.

    Handbook Reference: Section 4.6:
        'A scanner rejects any numeric literal not on an allowlist
        (section numbers, years that appear in a ledger quantity's period, list indices).'
    """
    allowed_section_numbers: FrozenSet[str] = field(default_factory=frozenset)
    allowed_years: FrozenSet[str] = field(default_factory=frozenset)
    allowed_list_indices: FrozenSet[str] = field(default_factory=frozenset)
    allowed_numbers: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class RenderResult:
    """Structured outcome of a report rendering and verification scan."""
    passed: bool
    rendered_text: str
    free_numbers: Tuple[str, ...]
    resolved_quantities: Tuple[Quantity, ...]
    errors: Tuple[str, ...]
    rejection_reason: str = ""

    def __bool__(self) -> bool:
        return self.passed


class ReportRenderer:
    """
    Renders prose reports with ledger chips and scans for unsupported free numbers.

    Handbook Reference: Section 4.6 (Rule G4).
    """

    PLACEHOLDER_REGEX: Pattern = re.compile(r"\{\{\s*q\s*:\s*([a-zA-Z0-9_\-\.]+)\s*\}\}")
    ANY_PLACEHOLDER_REGEX: Pattern = re.compile(r"\{\{[^}]*\}\}")
    QUOTE_REGEX: Pattern = re.compile(
        r'(?:"[^"\\]*(?:\\.[^"\\]*)*"|“[^”]*”|>[^\n]+)\s*\([^)]*\b(?:p\.|pp\.|page|pages|table|para|paragraph|clause|section|vol\.)\s*\d+[^)]*\)',
        re.IGNORECASE,
    )
    LOCATOR_REGEX: Pattern = re.compile(r"\b(?:p\.|pp\.|page|pages|para|paragraph|table|clause|vol\.)\s*\d+(?:-\d+)?\b", re.IGNORECASE)
    SECTION_REGEX: Pattern = re.compile(
        r"\b(?:Section|Part|Step|Phase|Table|Figure)\s+\d+(?:\.\d+)*\b|(?:^|[\n\r])\s*#{0,6}\s*\d+\.\d+(?:\.\d+)*\b",
        re.IGNORECASE,
    )
    LIST_INDEX_REGEX: Pattern = re.compile(r"(?:^|[\n\r]|\s)(?:\d+\.|\d+\)|\(\d+\)|\[\d+\])(?=\s)", re.MULTILINE)
    NUMBER_REGEX: Pattern = re.compile(r"(?:[₹$€£]\s*)?-?\b\d+(?:,\d+)*(?:\.\d+)?%?(?=\s|[.,;:!?)\"']|$)")

    def __init__(self, verifier: Optional[LedgerVerifier] = None) -> None:
        self.verifier = verifier if verifier is not None else LedgerVerifier()

    def format_chip(self, quantity: Quantity) -> str:
        """
        Format a verified Quantity into a clickable chip representation.

        Handbook Reference: Section 4.6:
            'The ReportRenderer substitutes each placeholder with the formatted value,
            unit and a clickable chip (class, resolution, as_of, link to the Evidence Graph).'
        """
        # Format numeric value
        if quantity.value.is_integer():
            val_str = f"{int(quantity.value):,}"
        else:
            val_str = f"{quantity.value:,.2f}"

        unit_str = f" {quantity.unit}" if quantity.unit and quantity.unit != "dimensionless" else ""

        # Resolution tier name
        res_map = {0: "NATION", 1: "STATE", 2: "DISTRICT", 3: "SUBDISTRICT", 4: "VILLAGE_URBAN", 5: "POINT"}
        res_name = res_map.get(quantity.resolution, f"RES_{quantity.resolution}")

        # Construct clickable chip
        chip = (
            f"{val_str}{unit_str} "
            f"[{quantity.kind.value} | {res_name} | {quantity.as_of} | evidence_graph:{quantity.id}]"
        )
        return chip

    def render(
        self,
        template: str,
        ledger: Ledger,
        allowlist: Optional[AllowlistConfig] = None,
    ) -> RenderResult:
        """
        Substitute {{q:UUID}} placeholders with formatted chips and scan for free numbers.

        Args:
            template: Prose draft containing {{q:UUID}} placeholders.
            ledger: Active Epistemic Ledger.
            allowlist: Optional explicit allowlist of section numbers or permitted literals.

        Returns:
            RenderResult with pass/fail status, rendered text, and any detected free numbers.
        """
        errors: List[str] = []
        resolved_quantities: List[Quantity] = []
        free_numbers: List[str] = []

        # Step 1: Collect allowable years from all ledger quantities
        ledger_years: Set[str] = set()
        for q in ledger:
            # Extract 4-digit years from as_of (e.g. '2026-10-20' -> '2026')
            year_matches = re.findall(r"\b(19\d\d|20\d\d)\b", str(q.as_of))
            ledger_years.update(year_matches)

        # Merge with provided allowlist
        allowed_years = ledger_years.union(allowlist.allowed_years if allowlist else ())
        allowed_sections = set(allowlist.allowed_section_numbers if allowlist else ())
        allowed_indices = set(allowlist.allowed_list_indices if allowlist else ())
        allowed_custom = set(allowlist.allowed_numbers if allowlist else ())

        # Step 2: Validate and resolve placeholders (detect both valid and malformed placeholders)
        chip_replacements: Dict[str, Tuple[str, Quantity]] = {}

        for match in self.ANY_PLACEHOLDER_REGEX.finditer(template):
            ph_text = match.group(0)
            valid_m = self.PLACEHOLDER_REGEX.match(ph_text)
            if not valid_m:
                errors.append(f"Malformed quantity placeholder '{ph_text}'. Must follow '{{{{q:UUID}}}}' syntax.")
                continue

            qid = valid_m.group(1).strip()

            if qid not in ledger:
                errors.append(f"Placeholder '{ph_text}' references unknown quantity ID '{qid}'.")
                continue

            q = ledger.get(qid)
            # Verify quantity against LedgerVerifier
            report = self.verifier.verify_quantity(q, ledger)
            if not report.passed:
                errors.append(f"Quantity '{qid}' in placeholder '{ph_text}' failed verification: {report.summary}")
                continue

            resolved_quantities.append(q)
            chip = self.format_chip(q)
            chip_replacements[ph_text] = (chip, q)

        # If any placeholder failed verification, syntax check, or lookup, reject immediately
        if errors:
            return RenderResult(
                passed=False,
                rendered_text=template,
                free_numbers=tuple(free_numbers),
                resolved_quantities=tuple(resolved_quantities),
                errors=tuple(errors),
                rejection_reason="; ".join(errors),
            )

        # Step 3: Free-Number Scanning
        # To scan accurately without falsely flagging numbers inside chips or quotes:
        # A. Protect quoted passages with explicit locators (Handbook 4.6)
        quoted_blocks: List[str] = []
        def _mask_quote(m: re.Match) -> str:
            idx = len(quoted_blocks)
            quoted_blocks.append(m.group(0))
            return f"__QUOTED_PASSAGE_{idx}__"

        masked_text = self.QUOTE_REGEX.sub(_mask_quote, template)

        # B. Protect authorized placeholders by replacing with unique token
        placeholder_tokens: List[str] = []
        def _mask_placeholder(m: re.Match) -> str:
            full_match = m.group(0)
            if full_match in chip_replacements:
                idx = len(placeholder_tokens)
                chip, _ = chip_replacements[full_match]
                placeholder_tokens.append(chip)
                return f"__CHIP_TOKEN_{idx}__"
            return full_match

        scan_text = self.ANY_PLACEHOLDER_REGEX.sub(_mask_placeholder, masked_text)

        # C. Scan for section numbers and list indices to permit them
        section_matches = set(self.SECTION_REGEX.findall(scan_text))
        list_index_matches = set(self.LIST_INDEX_REGEX.findall(scan_text))
        locator_matches = set(self.LOCATOR_REGEX.findall(scan_text))

        # D. Scan for all numeric literals
        for num_match in self.NUMBER_REGEX.finditer(scan_text):
            raw_literal = num_match.group(0).strip()
            # Clean digits only (stripping currency/percent/commas for comparison)
            clean_digits = re.sub(r"[^\d.]", "", raw_literal)

            # Check allowlist criteria
            if clean_digits in allowed_years or raw_literal in allowed_years:
                continue

            if clean_digits in allowed_custom or raw_literal in allowed_custom:
                continue

            if any(raw_literal in s or clean_digits in s for s in section_matches):
                continue

            if any(raw_literal in s or clean_digits in s for s in allowed_sections):
                continue

            if any(raw_literal in li or clean_digits in li for li in list_index_matches):
                continue

            if any(raw_literal in li or clean_digits in li for li in allowed_indices):
                continue

            if any(raw_literal in loc or clean_digits in loc for loc in locator_matches):
                continue

            # Check if this literal is part of a list index or section number in context
            start_pos, end_pos = num_match.span()
            surrounding = scan_text[max(0, start_pos - 15):min(len(scan_text), end_pos + 15)]
            if re.search(r"(?:Section|Part|Step|Phase|Table|Figure)\s+" + re.escape(raw_literal), surrounding, re.IGNORECASE):
                continue
            if re.search(r"(?:p\.|pp\.|page|pages|para|table|clause)\s*" + re.escape(raw_literal), surrounding, re.IGNORECASE):
                continue
            if re.search(r"(?:^|[\n\r])\s*" + re.escape(raw_literal) + r"\.\s+", surrounding):
                continue


            # If not allowlisted, flag as forbidden free number
            free_numbers.append(raw_literal)

        # Step 4: Render final text by restoring chips and unmasking quotes
        rendered_text = scan_text
        for idx, chip in enumerate(placeholder_tokens):
            rendered_text = rendered_text.replace(f"__CHIP_TOKEN_{idx}__", chip)

        for idx, quote in enumerate(quoted_blocks):
            rendered_text = rendered_text.replace(f"__QUOTED_PASSAGE_{idx}__", quote)

        # Step 5: Evaluate rejection
        passed = (len(free_numbers) == 0) and (len(errors) == 0)
        rejection_reason = ""
        if not passed:
            reasons = []
            if free_numbers:
                reasons.append(
                    f"Free number scanner rejected report: found {len(free_numbers)} "
                    f"unsupported numeric literal(s) not on allowlist: {free_numbers} (Handbook 4.6, Rule G4)."
                )
            if errors:
                reasons.extend(errors)
            rejection_reason = " ".join(reasons)

        return RenderResult(
            passed=passed,
            rendered_text=rendered_text,
            free_numbers=tuple(free_numbers),
            resolved_quantities=tuple(resolved_quantities),
            errors=tuple(errors),
            rejection_reason=rejection_reason,
        )
