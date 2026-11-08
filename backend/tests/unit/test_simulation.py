from math import inf

import pytest
from backend.arthlens.domain.simulation import SimulationMetadata
from backend.arthlens.simulation import (
    SimulationOutcome,
    run_monte_carlo,
    run_one_at_a_time_sensitivity,
)


def _metadata(*, seed=17, sample_count=1000):
    return SimulationMetadata(
        scenario_id="baseline",
        model_version="test-v1",
        seed=seed,
        sample_count=sample_count,
        data_versions=("fixture-v1",),
    )


def _run(seed=17):
    def sample(rng):
        demand = rng.normal(100, 10)
        return SimulationOutcome(
            metrics={"revenue": demand * 2, "minimum_cash": demand - 105},
            cash_shortfall=demand < 95,
        )

    return run_monte_carlo(
        sample,
        metadata=_metadata(seed=seed),
        quantile_levels=(0.1, 0.5, 0.9),
        minimum_sample_count=500,
        convergence_tolerances={"revenue": 2, "minimum_cash": 1},
        shortfall_probability_tolerance=0.02,
    )


def test_monte_carlo_uses_reproducible_pcg64_and_reports_statistics():
    first = _run()
    second = _run()

    assert first == second
    assert first.metadata == _metadata()
    assert first.metrics["revenue"].mean == pytest.approx(200, abs=1)
    assert first.metrics["revenue"].quantiles[0.5] == pytest.approx(200, abs=1.5)
    assert first.metrics["revenue"].standard_error > 0
    assert 0 < first.shortfall_probability < 1
    assert first.shortfall_probability_standard_error > 0
    assert first.converged


def test_monte_carlo_changes_output_for_a_different_seed():
    assert _run(17).metrics != _run(18).metrics


def test_monte_carlo_rejects_mismatched_metrics_and_invalid_convergence_contract():
    sample_count = 0

    def inconsistent_sample(rng):
        nonlocal sample_count
        sample_count += 1
        metric_name = "first" if sample_count == 1 else "second"
        return SimulationOutcome({metric_name: 1}, False)

    with pytest.raises(ValueError, match="different set of metrics"):
        run_monte_carlo(
            inconsistent_sample,
            metadata=_metadata(sample_count=2),
            quantile_levels=(0.5,),
            minimum_sample_count=2,
            convergence_tolerances={"first": 1},
            shortfall_probability_tolerance=1,
        )

    with pytest.raises(ValueError, match="between 2 and sample_count"):
        run_monte_carlo(
            lambda rng: SimulationOutcome({"value": 1}, False),
            metadata=_metadata(sample_count=2),
            quantile_levels=(0.5,),
            minimum_sample_count=3,
            convergence_tolerances={"value": 1},
            shortfall_probability_tolerance=1,
        )


def test_monte_carlo_records_nonconvergence_when_explicit_tolerance_is_not_met():
    result = run_monte_carlo(
        lambda rng: SimulationOutcome(
            {"value": float(rng.random())},
            cash_shortfall=bool(rng.random() < 0.5),
        ),
        metadata=_metadata(sample_count=20),
        quantile_levels=(0.5,),
        minimum_sample_count=20,
        convergence_tolerances={"value": 0},
        shortfall_probability_tolerance=0,
    )

    assert not result.metrics["value"].converged
    assert not result.shortfall_probability_converged
    assert not result.converged


def test_zero_observed_shortfalls_do_not_claim_probability_convergence():
    result = run_monte_carlo(
        lambda rng: SimulationOutcome({"value": 1}, cash_shortfall=False),
        metadata=_metadata(sample_count=20),
        quantile_levels=(0.5,),
        minimum_sample_count=20,
        convergence_tolerances={"value": 0},
        shortfall_probability_tolerance=1,
    )

    assert result.shortfall_probability == 0
    assert not result.shortfall_probability_converged
    assert not result.converged


def test_simulation_outcome_rejects_nonfinite_metrics():
    with pytest.raises(ValueError, match="must be finite"):
        SimulationOutcome({"value": inf}, False)


def test_one_at_a_time_sensitivity_changes_only_the_named_parameter_and_reports_deltas():
    observed_inputs = []

    def evaluate(parameters):
        observed_inputs.append(dict(parameters))
        return {
            "revenue": parameters["price"] * parameters["quantity"],
            "cost": parameters["unit_cost"] * parameters["quantity"],
        }

    result = run_one_at_a_time_sensitivity(
        evaluate,
        baseline_parameters={"price": 10, "unit_cost": 4, "quantity": 5},
        parameter_values={"price": (8, 12), "quantity": (4, 6)},
    )

    assert result.baseline_outputs == {"revenue": 50, "cost": 20}
    assert [point.deltas for point in result.points] == [
        {"revenue": -10, "cost": 0},
        {"revenue": 10, "cost": 0},
        {"revenue": -10, "cost": -4},
        {"revenue": 10, "cost": 4},
    ]
    baseline = observed_inputs[0]
    for changed in observed_inputs[1:]:
        differences = {key for key in baseline if baseline[key] != changed[key]}
        assert len(differences) == 1


def test_one_at_a_time_sensitivity_rejects_unknown_parameters_and_output_shape_changes():
    with pytest.raises(ValueError, match="Unknown sensitivity parameter"):
        run_one_at_a_time_sensitivity(
            lambda parameters: {"output": 1},
            baseline_parameters={"known": 1},
            parameter_values={"unknown": (2,)},
        )

    calls = 0

    def changing_evaluator(parameters):
        nonlocal calls
        calls += 1
        return {"baseline": 1} if calls == 1 else {"different": 1}

    with pytest.raises(ValueError, match="same output names"):
        run_one_at_a_time_sensitivity(
            changing_evaluator,
            baseline_parameters={"parameter": 1},
            parameter_values={"parameter": (2,)},
        )
