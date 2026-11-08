"""Scenario-driven spatial demand allocation strategies."""

from dataclasses import dataclass
from math import fsum, isfinite
from types import MappingProxyType
from typing import Mapping, Sequence

import numpy as np

from backend.arthlens.domain.interfaces import DemandAllocator


@dataclass(frozen=True)
class DemandZone:
    id: str
    demand: float

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Demand zone ID is required.")
        try:
            demand = float(self.demand)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Zone demand must be numeric.") from exc
        if not isfinite(demand) or demand < 0:
            raise ValueError("Zone demand must be finite and non-negative.")
        object.__setattr__(self, "demand", demand)


@dataclass(frozen=True)
class Facility:
    id: str
    attractiveness: float

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Facility ID is required.")
        try:
            attractiveness = float(self.attractiveness)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Facility attractiveness must be numeric.") from exc
        if not isfinite(attractiveness) or attractiveness < 0:
            raise ValueError("Facility attractiveness must be finite and non-negative.")
        object.__setattr__(self, "attractiveness", attractiveness)


@dataclass(frozen=True)
class AllocationParameters:
    travel_time_minutes_by_pair: Mapping[tuple[str, str], float]
    distance_decay_exponent: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.travel_time_minutes_by_pair, Mapping):
            raise TypeError("travel_time_minutes_by_pair must be a mapping.")
        travel_times: dict[tuple[str, str], float] = {}
        for pair, raw_minutes in self.travel_time_minutes_by_pair.items():
            if (
                not isinstance(pair, tuple)
                or len(pair) != 2
                or not all(isinstance(item, str) and item for item in pair)
            ):
                raise ValueError("Travel-time keys must be (zone_id, facility_id) string pairs.")
            try:
                minutes = float(raw_minutes)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("Travel times must be numeric.") from exc
            if not isfinite(minutes) or minutes < 0:
                raise ValueError("Travel times must be finite and non-negative.")
            travel_times[pair] = minutes
        if self.distance_decay_exponent is not None:
            try:
                decay = float(self.distance_decay_exponent)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("distance_decay_exponent must be numeric.") from exc
            if not isfinite(decay) or decay <= 0:
                raise ValueError("distance_decay_exponent must be finite and positive.")
            object.__setattr__(self, "distance_decay_exponent", decay)
        object.__setattr__(self, "travel_time_minutes_by_pair", MappingProxyType(travel_times))


@dataclass(frozen=True)
class Allocation:
    method_id: str
    probabilities_by_zone: Mapping[str, Mapping[str, float]]
    demand_by_zone: Mapping[str, Mapping[str, float]]
    facility_demand: Mapping[str, float]
    total_demand: float
    model_parameters: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "probabilities_by_zone",
            MappingProxyType(
                {
                    zone_id: MappingProxyType(dict(probabilities))
                    for zone_id, probabilities in self.probabilities_by_zone.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "demand_by_zone",
            MappingProxyType(
                {
                    zone_id: MappingProxyType(dict(demand))
                    for zone_id, demand in self.demand_by_zone.items()
                }
            ),
        )
        object.__setattr__(self, "facility_demand", MappingProxyType(dict(self.facility_demand)))
        object.__setattr__(self, "model_parameters", MappingProxyType(dict(self.model_parameters)))


class NearestFacilityAllocator(DemandAllocator):
    """Assign each demand zone to the closest facility by travel time."""

    def allocate(
        self,
        zones: Sequence[DemandZone],
        facilities: Sequence[Facility],
        params: AllocationParameters,
    ) -> Allocation:
        ordered_zones, ordered_facilities = _validate_problem(zones, facilities, params)
        probabilities: dict[str, dict[str, float]] = {}
        for zone in ordered_zones:
            closest = min(
                ordered_facilities,
                key=lambda facility: (
                    params.travel_time_minutes_by_pair[(zone.id, facility.id)],
                    facility.id,
                ),
            )
            probabilities[zone.id] = {
                facility.id: float(facility.id == closest.id)
                for facility in ordered_facilities
            }
        return _build_allocation(
            method_id="nearest_v1",
            zones=ordered_zones,
            facilities=ordered_facilities,
            probabilities=probabilities,
            model_parameters={},
        )


class HuffAllocator(DemandAllocator):
    """Allocate demand using the Huff gravity model and explicit scenario lambda."""

    def allocate(
        self,
        zones: Sequence[DemandZone],
        facilities: Sequence[Facility],
        params: AllocationParameters,
    ) -> Allocation:
        ordered_zones, ordered_facilities = _validate_problem(zones, facilities, params)
        decay = params.distance_decay_exponent
        if decay is None:
            raise ValueError("Huff allocation requires an explicit distance-decay scenario input.")

        probabilities: dict[str, dict[str, float]] = {}
        attractiveness = np.asarray(
            [facility.attractiveness for facility in ordered_facilities],
            dtype=np.float64,
        )
        for zone in ordered_zones:
            travel_times = np.asarray(
                [
                    params.travel_time_minutes_by_pair[(zone.id, facility.id)]
                    for facility in ordered_facilities
                ],
                dtype=np.float64,
            )
            positive_attractiveness = attractiveness > 0
            if not positive_attractiveness.any():
                raise ValueError(f"Zone '{zone.id}' has no facility with positive attractiveness.")
            zero_time = (travel_times == 0) & positive_attractiveness
            if zero_time.any():
                # The zero-time limit leaves only co-located facilities in the choice set.
                weights = np.where(zero_time, attractiveness, 0.0)
                weights /= float(np.max(weights))
            else:
                log_times = np.log(travel_times[positive_attractiveness])
                min_log_time = float(np.min(log_times))
                with np.errstate(over="ignore"):
                    penalties = decay * (log_times - min_log_time)
                log_weights = np.full(attractiveness.shape, float("-inf"))
                log_weights[positive_attractiveness] = (
                    np.log(attractiveness[positive_attractiveness]) - penalties
                )
                max_log_weight = float(np.max(log_weights))
                if not isfinite(max_log_weight):
                    raise ValueError(
                        f"Huff weights for zone '{zone.id}' cannot be represented for these inputs."
                    )
                weights = np.exp(log_weights - max_log_weight)
            weight_total = float(np.sum(weights))
            if not isfinite(weight_total) or weight_total <= 0:
                raise ValueError(f"Zone '{zone.id}' has no representable positive Huff weight.")
            row = weights / weight_total
            largest_index = int(np.argmax(row))
            row[largest_index] = max(
                0.0,
                1.0 - fsum(
                    float(probability)
                    for index, probability in enumerate(row)
                    if index != largest_index
                ),
            )
            probabilities[zone.id] = {
                facility.id: float(row[index])
                for index, facility in enumerate(ordered_facilities)
            }

        return _build_allocation(
            method_id="huff_v1",
            zones=ordered_zones,
            facilities=ordered_facilities,
            probabilities=probabilities,
            model_parameters={"distance_decay_exponent": decay},
        )


def _validate_problem(
    zones: Sequence[DemandZone],
    facilities: Sequence[Facility],
    params: AllocationParameters,
) -> tuple[tuple[DemandZone, ...], tuple[Facility, ...]]:
    if not isinstance(params, AllocationParameters):
        raise TypeError("params must be an AllocationParameters instance.")
    zones = tuple(zones)
    facilities = tuple(facilities)
    if any(not isinstance(zone, DemandZone) for zone in zones):
        raise TypeError("zones must contain DemandZone instances.")
    if any(not isinstance(facility, Facility) for facility in facilities):
        raise TypeError("facilities must contain Facility instances.")
    ordered_zones = tuple(sorted(zones, key=lambda zone: zone.id))
    ordered_facilities = tuple(sorted(facilities, key=lambda facility: facility.id))
    if not ordered_zones or not ordered_facilities:
        raise ValueError("Demand allocation requires at least one zone and one facility.")
    if len({zone.id for zone in ordered_zones}) != len(ordered_zones):
        raise ValueError("Demand zone IDs must be unique.")
    if len({facility.id for facility in ordered_facilities}) != len(ordered_facilities):
        raise ValueError("Facility IDs must be unique.")

    expected_pairs = {
        (zone.id, facility.id)
        for zone in ordered_zones
        for facility in ordered_facilities
    }
    supplied_pairs = set(params.travel_time_minutes_by_pair)
    if expected_pairs != supplied_pairs:
        missing = sorted(expected_pairs - supplied_pairs)
        extra = sorted(supplied_pairs - expected_pairs)
        raise ValueError(
            f"Travel-time matrix does not match allocation inputs; missing={missing[:3]}, "
            f"extra={extra[:3]}."
        )
    return ordered_zones, ordered_facilities


def _build_allocation(
    *,
    method_id: str,
    zones: Sequence[DemandZone],
    facilities: Sequence[Facility],
    probabilities: Mapping[str, Mapping[str, float]],
    model_parameters: Mapping[str, float],
) -> Allocation:
    demand_by_zone: dict[str, dict[str, float]] = {}
    for zone in zones:
        probabilities_for_zone = probabilities[zone.id]
        largest = max(probabilities_for_zone, key=probabilities_for_zone.get)
        row = {
            facility.id: zone.demand * probabilities_for_zone[facility.id]
            for facility in facilities
            if facility.id != largest
        }
        row[largest] = zone.demand - fsum(row.values())
        demand_by_zone[zone.id] = {
            facility.id: row[facility.id] for facility in facilities
        }

    facility_demand = {
        facility.id: fsum(demand_by_zone[zone.id][facility.id] for zone in zones)
        for facility in facilities
    }
    return Allocation(
        method_id=method_id,
        probabilities_by_zone=probabilities,
        demand_by_zone=demand_by_zone,
        facility_demand=facility_demand,
        total_demand=fsum(zone.demand for zone in zones),
        model_parameters=model_parameters,
    )


__all__ = [
    "Allocation",
    "AllocationParameters",
    "DemandAllocator",
    "DemandZone",
    "Facility",
    "HuffAllocator",
    "NearestFacilityAllocator",
]
