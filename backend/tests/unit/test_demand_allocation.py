import pytest
from backend.arthlens.demand.allocator import (
    AllocationParameters,
    DemandZone,
    Facility,
    HuffAllocator,
    NearestFacilityAllocator,
)


def _assert_allocation_contract(allocation, zones, facilities):
    assert set(allocation.probabilities_by_zone) == {zone.id for zone in zones}
    assert set(allocation.facility_demand) == {facility.id for facility in facilities}
    for zone in zones:
        assert sum(allocation.probabilities_by_zone[zone.id].values()) == pytest.approx(1.0)
        assert sum(allocation.demand_by_zone[zone.id].values()) == pytest.approx(zone.demand)
    assert sum(allocation.facility_demand.values()) == pytest.approx(allocation.total_demand)


def test_nearest_allocator_assigns_each_zone_to_closest_facility_and_conserves_demand():
    zones = (DemandZone("zone-1", 100), DemandZone("zone-2", 50))
    facilities = (Facility("facility-b", 1), Facility("facility-a", 1))
    params = AllocationParameters(
        {
            ("zone-1", "facility-a"): 4,
            ("zone-1", "facility-b"): 8,
            ("zone-2", "facility-a"): 5,
            ("zone-2", "facility-b"): 5,
        }
    )

    allocation = NearestFacilityAllocator().allocate(zones, facilities, params)

    assert allocation.method_id == "nearest_v1"
    assert allocation.probabilities_by_zone["zone-1"] == {
        "facility-a": 1.0,
        "facility-b": 0.0,
    }
    assert allocation.probabilities_by_zone["zone-2"] == {
        "facility-a": 1.0,
        "facility-b": 0.0,
    }
    _assert_allocation_contract(allocation, zones, facilities)


def test_huff_allocator_matches_gravity_formula_and_conserves_demand():
    zones = (DemandZone("zone-1", 90),)
    facilities = (Facility("facility-a", 4), Facility("facility-b", 2))
    params = AllocationParameters(
        {
            ("zone-1", "facility-a"): 2,
            ("zone-1", "facility-b"): 4,
        },
        distance_decay_exponent=2,
    )

    allocation = HuffAllocator().allocate(zones, facilities, params)

    assert allocation.method_id == "huff_v1"
    assert allocation.probabilities_by_zone["zone-1"]["facility-a"] == pytest.approx(8 / 9)
    assert allocation.probabilities_by_zone["zone-1"]["facility-b"] == pytest.approx(1 / 9)
    assert allocation.demand_by_zone["zone-1"]["facility-a"] == pytest.approx(80)
    assert allocation.demand_by_zone["zone-1"]["facility-b"] == pytest.approx(10)
    assert allocation.model_parameters == {"distance_decay_exponent": 2}
    _assert_allocation_contract(allocation, zones, facilities)


def test_large_huff_decay_converges_to_nearest_facility_without_overflow():
    zones = (DemandZone("zone-1", 75),)
    facilities = (Facility("near", 1), Facility("far", 1))
    params = AllocationParameters(
        {
            ("zone-1", "near"): 1,
            ("zone-1", "far"): 2,
        },
        distance_decay_exponent=10_000,
    )

    allocation = HuffAllocator().allocate(zones, facilities, params)

    assert allocation.probabilities_by_zone["zone-1"]["near"] == 1
    assert allocation.probabilities_by_zone["zone-1"]["far"] == 0
    assert allocation.facility_demand == {"far": 0, "near": 75}
    _assert_allocation_contract(allocation, zones, facilities)


def test_huff_zero_travel_time_uses_only_co_located_facilities():
    zones = (DemandZone("zone-1", 40),)
    facilities = (Facility("at-origin-a", 1), Facility("at-origin-b", 3), Facility("far", 10))
    params = AllocationParameters(
        {
            ("zone-1", "at-origin-a"): 0,
            ("zone-1", "at-origin-b"): 0,
            ("zone-1", "far"): 5,
        },
        distance_decay_exponent=1,
    )

    allocation = HuffAllocator().allocate(zones, facilities, params)

    assert allocation.probabilities_by_zone["zone-1"] == {
        "at-origin-a": pytest.approx(0.25),
        "at-origin-b": pytest.approx(0.75),
        "far": 0,
    }
    _assert_allocation_contract(allocation, zones, facilities)


@pytest.mark.parametrize("allocator", [NearestFacilityAllocator(), HuffAllocator()])
def test_allocators_reject_incomplete_or_invalid_scenario_inputs(allocator):
    with pytest.raises(ValueError, match="at least one zone and one facility"):
        allocator.allocate(
            (),
            (Facility("facility", 1),),
            AllocationParameters({}),
        )

    with pytest.raises(ValueError, match="Travel-time matrix does not match"):
        allocator.allocate(
            (DemandZone("zone", 1),),
            (Facility("facility", 1),),
            AllocationParameters({}),
        )

    with pytest.raises(ValueError, match="finite and non-negative"):
        AllocationParameters({("zone", "facility"): float("inf")})


def test_huff_requires_explicit_positive_decay_and_nonzero_attractiveness():
    zones = (DemandZone("zone", 1),)
    facilities = (Facility("facility", 0),)
    params = AllocationParameters({("zone", "facility"): 1})

    with pytest.raises(ValueError, match="explicit distance-decay"):
        HuffAllocator().allocate(zones, facilities, params)

    with pytest.raises(ValueError, match="positive attractiveness"):
        HuffAllocator().allocate(
            zones,
            facilities,
            AllocationParameters(
                {("zone", "facility"): 1},
                distance_decay_exponent=1,
            ),
        )
