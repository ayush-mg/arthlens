"""
Property-based tests for Monetary Arithmetic and Accounting Invariants.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Module 13: Financial Correctness, Invariants & Hypothesis Property Testing.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import uuid
import pytest
from hypothesis import given, strategies as st

from backend.arthlens.domain.business import (
    Money,
    JournalEntry,
    JournalEntryLine,
    UnbalancedJournalEntryError,
)


@st.composite
def money_strategy(draw):
    """Generates valid monetary amounts between -1,000,000,000 and +1,000,000,000."""
    val = draw(st.decimals(min_value=-1000000000, max_value=1000000000, places=2))
    return Money(val)


class TestMoneyPropertyInvariants:
    """Hypothesis Property-Based Invariant Verification for Money."""

    @given(money_strategy(), money_strategy())
    def test_money_addition_commutativity(self, a: Money, b: Money):
        """Property: a + b == b + a."""
        assert a + b == b + a

    @given(money_strategy(), money_strategy(), money_strategy())
    def test_money_addition_associativity(self, a: Money, b: Money, c: Money):
        """Property: (a + b) + c == a + (b + c)."""
        assert (a + b) + c == a + (b + c)

    @given(money_strategy())
    def test_money_additive_identity(self, a: Money):
        """Property: a + 0 == a and a - 0 == a."""
        zero = Money.zero()
        assert a + zero == a
        assert a - zero == a

    @given(money_strategy(), money_strategy())
    def test_money_subtraction_inverse(self, a: Money, b: Money):
        """Property: (a + b) - b == a."""
        assert (a + b) - b == a

    @given(st.floats(min_value=-10000000, max_value=10000000, allow_nan=False, allow_infinity=False))
    def test_money_always_quantized_to_two_decimal_places(self, val: float):
        """Property: Money always quantizes to exactly 2 decimal places with zero float drift."""
        m = Money.from_float(val)
        assert m.amount.as_tuple().exponent == -2

    @given(money_strategy())
    def test_money_exact_multiplication_by_integer(self, a: Money):
        """Property: a * 3 == a + a + a."""
        assert a * 3 == a + a + a


class TestGeneralLedgerInvariants:
    """Invariant checks for double-entry bookkeeping."""

    @given(st.lists(st.decimals(min_value=1, max_value=500000, places=2), min_size=1, max_size=10))
    def test_journal_entry_enforces_balanced_debits_and_credits(self, line_amounts):
        """Every posted journal entry must satisfy sum(debit) == sum(credit) or raise UnbalancedJournalEntryError."""
        lines = []
        total = Decimal("0.00")
        for amt in line_amounts:
            lines.append(JournalEntryLine(
                id=uuid.uuid4(),
                journal_entry_id=uuid.uuid4(),
                account_code="1000",
                account_name="Cash",
                debit=Money(amt),
                credit=Money.zero(),
            ))
            total += amt

        # Add single balancing credit line
        lines.append(JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=uuid.uuid4(),
            account_code="4000",
            account_name="Revenue",
            debit=Money.zero(),
            credit=Money(total),
        ))

        # Balanced entry succeeds
        entry = JournalEntry(
            id=uuid.uuid4(),
            business_id=uuid.uuid4(),
            entry_number="JE-PROP-001",
            entry_date=date.today(),
            reference_type="MANUAL",
            description="Hypothesis balanced journal entry",
            lines=lines,
        )
        assert entry.total_debits == entry.total_credits

        # Tampering with credit raises UnbalancedJournalEntryError
        tampered_lines = list(lines)
        tampered_lines[-1] = JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=uuid.uuid4(),
            account_code="4000",
            account_name="Revenue",
            debit=Money.zero(),
            credit=Money(total + Decimal("0.05")),
        )
        with pytest.raises(UnbalancedJournalEntryError):
            JournalEntry(
                id=uuid.uuid4(),
                business_id=uuid.uuid4(),
                entry_number="JE-PROP-FAIL",
                entry_date=date.today(),
                reference_type="MANUAL",
                description="Hypothesis unbalanced entry attempt",
                lines=tampered_lines,
            )
