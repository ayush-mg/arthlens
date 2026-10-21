"""
Staleness detection and quality flag assignment based on configured source age.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.4, 4.7).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).

Properties:
- Each source has a configured maximum age (max_age_days).
- Quantities exceeding their source maximum age receive the STALE quality flag.
- Derived quantities inherit STALE and all parent quality flags through propagation.
"""

from dataclasses import replace
from datetime import date, datetime
from typing import Optional, Union

from backend.arthlens.domain.quantity import Quantity


def parse_as_of_date(as_of: Union[str, date, datetime]) -> date:
    """
    Parse a temporal support representation (as_of) into a standard datetime.date.

    Supports:
        - date or datetime instances.
        - ISO date strings: 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS'.
        - 4-digit year strings: 'YYYY' (defaults to Jan 1 of that year).
        - Date intervals: 'YYYY-MM-DD/YYYY-MM-DD' (uses end date).
    """
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    if isinstance(as_of, str):
        clean = as_of.strip()
        # Handle interval: take end date
        if "/" in clean:
            clean = clean.split("/")[-1].strip()
        # Handle 4-digit year
        if len(clean) == 4 and clean.isdigit():
            return date(int(clean), 1, 1)
        # Handle ISO date prefix
        if len(clean) >= 10:
            return date.fromisoformat(clean[:10])
        return date.fromisoformat(clean)

    raise TypeError(f"Cannot parse as_of date from type {type(as_of)}: {as_of}")


def is_source_stale(
    as_of: Union[str, date, datetime],
    max_age_days: int,
    reference_date: Optional[Union[str, date, datetime]] = None,
) -> bool:
    """
    Determine if an observation's as_of date exceeds its source's configured maximum age.

    Handbook Reference: Section 4.4:
        'Each source has a configured maximum age. Beyond it the quantity
        gets the STALE flag; derived quantities inherit STALE.'

    Args:
        as_of: Temporal support date of the quantity.
        max_age_days: Explicit maximum age allowed for this source in days.
        reference_date: Reference date to compare against (defaults to date.today()).

    Returns:
        True if the elapsed days strictly exceed max_age_days, False otherwise.

    Raises:
        ValueError: If max_age_days is negative.
    """
    if not isinstance(max_age_days, int) or max_age_days < 0:
        raise ValueError(f"max_age_days must be a non-negative integer, got {max_age_days}")

    as_of_date = parse_as_of_date(as_of)
    ref_date = parse_as_of_date(reference_date) if reference_date is not None else date.today()

    elapsed_days = (ref_date - as_of_date).days
    return elapsed_days > max_age_days


def apply_staleness_flag(
    quality_flags: frozenset,
    as_of: Union[str, date, datetime],
    max_age_days: int,
    reference_date: Optional[Union[str, date, datetime]] = None,
) -> frozenset:
    """
    Return an updated quality_flags frozenset with 'STALE' included if max_age_days is exceeded.
    """
    if is_source_stale(as_of, max_age_days=max_age_days, reference_date=reference_date):
        if "STALE" in quality_flags:
            return quality_flags
        return frozenset(set(quality_flags) | {"STALE"})
    return quality_flags


def with_staleness_flag(
    quantity: Quantity,
    max_age_days: int,
    reference_date: Optional[Union[str, date, datetime]] = None,
) -> Quantity:
    """
    Return a new Quantity instance with the 'STALE' quality flag applied if it exceeds max_age_days.

    If the quantity is within its configured maximum age, returns the original instance.
    """
    new_flags = apply_staleness_flag(
        quantity.quality_flags,
        as_of=quantity.as_of,
        max_age_days=max_age_days,
        reference_date=reference_date,
    )
    if new_flags == quantity.quality_flags:
        return quantity
    return replace(quantity, quality_flags=new_flags)
