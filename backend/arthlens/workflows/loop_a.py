"""
Loop A: Spatial Siting & Micro-enterprise Demand Allocation Workflow.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 2.3, 6.2-6.3, 8.8).
Phase: P5-1 (End-to-End Workflow Loops).
"""

import uuid
from dataclasses import dataclass
from typing import Mapping

from backend.arthlens.demand.allocator import (
    AllocationParameters,
    DemandZone,
    Facility,
    HuffAllocator,
    NearestFacilityAllocator,
)
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.ledger import Ledger


@dataclass(frozen=True)
class LoopAResult:
    territory_id: str
    facility_id: str
    allocator_used: str
    status: str
    captured_demand_inr_monthly: float | None
    market_share_fraction: float | None
    total_market_demand_inr: float | None
    missing_evidence: tuple[str, ...]
    quantities: tuple[Quantity, ...]


@dataclass(frozen=True)
class SpatialDemandInputs:
    """Explicit, traceable inputs for a spatial allocation run.

    Each referenced quantity must already be registered in the ledger. This
    keeps observed data and user/scenario assumptions distinct from the
    deterministic allocation calculation.
    """

    zones: tuple[DemandZone, ...]
    facilities: tuple[Facility, ...]
    parameters: AllocationParameters
    provenance_by_input: Mapping[str, str]


def run_loop_a_spatial_siting(
    ledger: Ledger,
    *,
    geo_unit_id: str = "in:district:120",
    enterprise_id: str = "fac_proposed_1",
    allocator_type: str = "huff",
    allocation_inputs: SpatialDemandInputs | None = None,
) -> LoopAResult:
    """
    Execute Loop A only when its demand, facility, and routing inputs are
    registered ledger quantities. It never manufactures zones, demand, routing
    times, competitor attributes, or a Huff decay value.
    """
    if allocation_inputs is None:
        return LoopAResult(
            territory_id=geo_unit_id,
            facility_id=enterprise_id,
            allocator_used=allocator_type,
            status="INSUFFICIENT_DATA",
            captured_demand_inr_monthly=None,
            market_share_fraction=None,
            total_market_demand_inr=None,
            missing_evidence=(
                "registered zone demand quantities",
                "registered facility attractiveness quantities",
                "registered route-derived travel-time quantities",
                "registered distance-decay scenario quantity",
            ),
            quantities=(),
        )

    required_provenance_keys = {
        *(f"zone_demand:{zone.id}" for zone in allocation_inputs.zones),
        *(f"facility_attractiveness:{facility.id}" for facility in allocation_inputs.facilities),
        *(
            f"travel_time:{zone.id}:{facility.id}"
            for zone in allocation_inputs.zones
            for facility in allocation_inputs.facilities
        ),
    }
    if allocator_type.lower() == "huff":
        required_provenance_keys.add("distance_decay_exponent")
    missing_provenance = tuple(
        sorted(required_provenance_keys - set(allocation_inputs.provenance_by_input))
    )
    if missing_provenance:
        return LoopAResult(
            territory_id=geo_unit_id,
            facility_id=enterprise_id,
            allocator_used=allocator_type,
            status="INSUFFICIENT_DATA",
            captured_demand_inr_monthly=None,
            market_share_fraction=None,
            total_market_demand_inr=None,
            missing_evidence=tuple(f"missing provenance for {item}" for item in missing_provenance),
            quantities=(),
        )

    input_quantity_ids = tuple(dict.fromkeys(allocation_inputs.provenance_by_input.values()))
    missing_quantity_ids = tuple(
        quantity_id
        for quantity_id in input_quantity_ids
        if quantity_id not in {quantity.id for quantity in ledger.quantities}
    )
    if missing_quantity_ids:
        return LoopAResult(
            territory_id=geo_unit_id,
            facility_id=enterprise_id,
            allocator_used=allocator_type,
            status="INSUFFICIENT_DATA",
            captured_demand_inr_monthly=None,
            market_share_fraction=None,
            total_market_demand_inr=None,
            missing_evidence=tuple(
                f"unregistered input quantity: {item}" for item in missing_quantity_ids
            ),
            quantities=(),
        )

    allocator = HuffAllocator() if allocator_type.lower() == "huff" else NearestFacilityAllocator()
    allocation = allocator.allocate(
        allocation_inputs.zones,
        allocation_inputs.facilities,
        allocation_inputs.parameters,
    )

    captured_demand = allocation.facility_demand.get(enterprise_id, 0.0)
    total_demand = sum(zone.demand for zone in allocation_inputs.zones)
    market_share = captured_demand / total_demand if total_demand > 0 else 0.0

    # 5. Register output quantities into Ledger
    demand_qty = Quantity(
        id=f"qty:demand:{uuid.uuid4().hex[:8]}",
        definition_key="demand.monthly",
        value=round(captured_demand, 2),
        unit="INR/month",
        kind=Kind.ESTIMATED,
        evidence_floor=min(
            ledger.get(quantity_id).evidence_floor for quantity_id in input_quantity_ids
        ),
        geo_unit_id=geo_unit_id,
        resolution=ResolutionTier.DISTRICT,
        as_of="",
        uncertainty="UNQUANTIFIED",
        source_refs=(),
        method_id=f"allocator:{allocator_type}",
        model_version="1.0.0",
        parent_ids=input_quantity_ids,
        quality_flags=frozenset(
            [
                "CALCULATED_HUFF_GRAVITY"
                if allocator_type.lower() == "huff"
                else "CALCULATED_NEAREST"
            ]
        ),
    )

    share_qty = Quantity(
        id=f"qty:share:{uuid.uuid4().hex[:8]}",
        definition_key="demand.market_share",
        value=round(market_share, 4),
        unit="share",
        kind=Kind.ESTIMATED,
        evidence_floor=demand_qty.evidence_floor,
        geo_unit_id=geo_unit_id,
        resolution=ResolutionTier.DISTRICT,
        as_of="",
        uncertainty="UNQUANTIFIED",
        source_refs=(),
        method_id=f"allocator:{allocator_type}",
        model_version="1.0.0",
        parent_ids=(demand_qty.id,),
        quality_flags=demand_qty.quality_flags,
    )

    ledger.register(demand_qty)
    ledger.register(share_qty)

    return LoopAResult(
        territory_id=geo_unit_id,
        facility_id=enterprise_id,
        allocator_used=allocator_type,
        status="COMPLETED",
        captured_demand_inr_monthly=demand_qty.value,
        market_share_fraction=share_qty.value,
        total_market_demand_inr=round(total_demand, 2),
        missing_evidence=(),
        quantities=(demand_qty, share_qty),
    )


__all__ = ["LoopAResult", "SpatialDemandInputs", "run_loop_a_spatial_siting"]
