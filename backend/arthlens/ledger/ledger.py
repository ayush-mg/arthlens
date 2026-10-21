"""
Epistemic Ledger core directed acyclic graph (DAG) and registry.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.1, 4.2, 4.7).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).

Properties:
- Quantities are immutable once registered.
- Directed acyclic graph: cycles and direct self-references are strictly rejected.
- Ancestors of a quantity are exactly its transitive parents.
- Preserves epistemic provenance combination invariants.
"""

from collections import defaultdict, deque
from typing import Dict, Iterator, Optional, Set

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.downscaling import DownscalingRegistry
from backend.arthlens.ledger.propagation import propagate_quality_flags


class Ledger:
    """
    In-memory epistemic ledger holding registered immutable Quantity records in a DAG.

    Handbook Reference: Section 4.1, 4.7.
    """

    def __init__(self) -> None:
        self._quantities: Dict[str, Quantity] = {}
        self._parents: Dict[str, Set[str]] = {}
        self._children: Dict[str, Set[str]] = defaultdict(set)

    def register(self, quantity: Quantity) -> str:
        """
        Register an immutable Quantity into the ledger DAG.

        Raises:
            ValueError: If a direct self-reference, directed cycle, or invalid provenance kind is detected.
            TypeError: If the input is not a Quantity instance.
        """
        if not isinstance(quantity, Quantity):
            raise TypeError(f"Expected Quantity instance, got {type(quantity)}")

        # Check 1: Direct self-reference
        if quantity.id in quantity.parent_ids:
            raise ValueError(f"Direct self-reference rejected: Quantity '{quantity.id}' cannot be its own parent.")

        # Check 2: Kind invariants (Handbook 4.2)
        # A derived quantity (having parents) cannot be labelled OBSERVED.
        if quantity.kind == Kind.OBSERVED and len(quantity.parent_ids) > 0:
            raise ValueError("A quantity with parent inputs cannot have kind OBSERVED (Handbook 4.2).")

        # Check 3: Cycle detection
        # If quantity.id is already an ancestor of any declared parent, registering would introduce a cycle.
        for pid in quantity.parent_ids:
            if pid == quantity.id:
                raise ValueError(f"Cycle detected: {quantity.id} references itself.")
            if pid in self._quantities:
                if quantity.id in self.ancestors(pid):
                    raise ValueError(
                        f"Cycle detected: Quantity '{quantity.id}' is an existing ancestor of parent '{pid}'."
                    )

        # Check 4: Resolution refinement check (Handbook 4.3)
        # Derived resolution is the coarsest parent resolution unless a registered downscaling method applies.
        if quantity.parent_ids:
            parent_resolutions = [
                self._quantities[pid].resolution
                for pid in quantity.parent_ids
                if pid in self._quantities
            ]
            if parent_resolutions:
                coarsest_res = min(parent_resolutions)
                if quantity.resolution > coarsest_res:
                    if not DownscalingRegistry.is_registered(quantity.method_id):
                        raise ValueError(
                            f"Resolution cannot refine from {coarsest_res} to {quantity.resolution} "
                            f"without a registered downscaling method (Handbook 4.3). Method '{quantity.method_id}' is not registered."
                        )
                    if quantity.kind != Kind.ESTIMATED:
                        raise ValueError(
                            f"Downscaled quantity must have kind ESTIMATED, got {quantity.kind} (Handbook 4.3)."
                        )
                    if quantity.evidence_floor > 2:
                        raise ValueError(
                            f"Downscaled quantity must have evidence_floor at most 2, got {quantity.evidence_floor} (Handbook 4.3)."
                        )

        # Check 5: Evidence floor derivation rule (Handbook 4.2, 4.3)
        # evidence_floor(child) = min(evidence_floor(parent) for parent in parents)
        # Exception (Handbook 4.3): Downscaling outputs have floor = min(parent_floors, 2).
        if quantity.parent_ids:
            parent_floors = [
                self._quantities[pid].evidence_floor
                for pid in quantity.parent_ids
                if pid in self._quantities
            ]
            if parent_floors:
                min_parent_floor = min(parent_floors)
                parent_resolutions = [
                    self._quantities[pid].resolution
                    for pid in quantity.parent_ids
                    if pid in self._quantities
                ]
                is_downscaling = (
                    bool(parent_resolutions)
                    and quantity.resolution > min(parent_resolutions)
                    and DownscalingRegistry.is_registered(quantity.method_id)
                )

                if is_downscaling:
                    expected_floor = min(min_parent_floor, 2)
                    if quantity.evidence_floor != expected_floor:
                        raise ValueError(
                            f"Downscaled quantity evidence floor must equal min(parent floors, 2) ({expected_floor}), "
                            f"got {quantity.evidence_floor} (Handbook 4.2, 4.3)."
                        )
                else:
                    if quantity.evidence_floor != min_parent_floor:
                        raise ValueError(
                            f"Derived quantity evidence floor must equal min of parents ({min_parent_floor}), "
                            f"got {quantity.evidence_floor} (Handbook 4.2)."
                        )

        # Check 6: Quality flags propagation (Handbook 4.4)
        # Derived quantities must inherit STALE and all parent quality flags.
        if quantity.parent_ids:
            parent_flags = [
                self._quantities[pid].quality_flags
                for pid in quantity.parent_ids
                if pid in self._quantities
            ]
            if parent_flags:
                inherited_flags = propagate_quality_flags(parent_flags)
                if not inherited_flags.issubset(quantity.quality_flags):
                    missing_flags = inherited_flags - quantity.quality_flags
                    raise ValueError(
                        f"Derived quantity must inherit parent quality flags (Handbook 4.4). "
                        f"Missing inherited flags: {sorted(missing_flags)}"
                    )


        # Store quantity and record DAG edges
        self._quantities[quantity.id] = quantity
        self._parents[quantity.id] = set(quantity.parent_ids)

        for pid in quantity.parent_ids:
            self._children[pid].add(quantity.id)

        return quantity.id

    def get(self, quantity_id: str) -> Quantity:
        """
        Retrieve a registered quantity by ID.

        Raises:
            KeyError: If the quantity does not exist in the ledger.
        """
        if quantity_id not in self._quantities:
            raise KeyError(f"Quantity with ID '{quantity_id}' not found in ledger.")
        return self._quantities[quantity_id]

    def ancestors(self, quantity_id: str) -> Set[str]:
        """
        Return the set of all transitive ancestor IDs for the specified quantity.

        Handbook Reference: Section 4.7 bullet 3:
        'Ancestors of a quantity are exactly its transitive parents.'
        """
        if quantity_id not in self._quantities:
            return set()

        ancestor_set: Set[str] = set()
        queue = deque(self._parents.get(quantity_id, set()))

        while queue:
            curr_id = queue.popleft()
            if curr_id not in ancestor_set:
                ancestor_set.add(curr_id)
                for parent in self._parents.get(curr_id, set()):
                    if parent not in ancestor_set:
                        queue.append(parent)


        return ancestor_set

    def descendants(self, quantity_id: str) -> Set[str]:
        """Return the set of all transitive descendant IDs for the specified quantity."""
        if quantity_id not in self._quantities:
            return set()

        descendant_set: Set[str] = set()
        queue = deque(self._children.get(quantity_id, set()))

        while queue:
            curr_id = queue.popleft()
            if curr_id not in descendant_set:
                descendant_set.add(curr_id)
                for child in self._children.get(curr_id, set()):
                    if child not in descendant_set:
                        queue.append(child)

        return descendant_set

    def __contains__(self, quantity_id: str) -> bool:
        return quantity_id in self._quantities

    def __len__(self) -> int:
        return len(self._quantities)

    def __iter__(self) -> Iterator[Quantity]:
        return iter(self._quantities.values())
