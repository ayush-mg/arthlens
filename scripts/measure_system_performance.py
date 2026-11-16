"""
ArthLens Business Operating System & Decision Intelligence Performance Measurement Suite.

Measures empirical p50/p95 API latency, engine job durations, and database query timings.
Authoritative Reference: ArthLens Final Product Vision & Architecture Handbook.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time
import uuid
from typing import Any

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.decision.engine import DecisionIntelligenceEngine
from backend.arthlens.finance.loans import (
    LoanTerms,
    MoratoriumInterestTreatment,
    SubsidyTreatment,
    build_loan_schedule,
)
from backend.arthlens.finance.projection import calculate_break_even_quantity
from backend.arthlens.infra.database import get_engine
from backend.arthlens.security.tokens import create_access_token


def _percentiles(values: list[float]) -> dict[str, Any]:
    """Compute min, p50, p95, and max for a sample series in milliseconds."""
    if not values:
        return {
            "iterations": 0,
            "min_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "max_ms": 0.0,
            "mean_ms": 0.0,
        }
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    p50_idx = int(n * 0.50)
    p95_idx = min(n - 1, int(n * 0.95))
    return {
        "iterations": n,
        "min_ms": round(sorted_vals[0] * 1000, 2),
        "mean_ms": round(statistics.mean(sorted_vals) * 1000, 2),
        "p50_ms": round(sorted_vals[p50_idx] * 1000, 2),
        "p95_ms": round(sorted_vals[p95_idx] * 1000, 2),
        "max_ms": round(sorted_vals[-1] * 1000, 2),
    }


def measure_api_latencies(client: TestClient, iterations: int = 30) -> dict[str, Any]:
    """Measure Business OS API endpoint latencies across multiple requests."""
    headers = {}
    try:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("SELECT id, email FROM users LIMIT 1")).first()
            if row:
                token, _ = create_access_token(str(row[0]), str(row[1]), ["entrepreneur", "user"])
                headers = {"Authorization": f"Bearer {token}"}
    except (SQLAlchemyError, RuntimeError):
        pass

    endpoints = [
        ("GET /health", "/health", {}),
        ("GET /auth/ping", "/auth/ping", {}),
        ("GET /businesses", "/businesses", headers),
    ]
    results = {}
    for label, path, req_headers in endpoints:
        durations = []
        for _ in range(iterations):
            start = time.perf_counter()
            res = client.get(path, headers=req_headers)
            duration = time.perf_counter() - start
            if res.status_code in (200, 401):  # 401 if unseeded DB, still valid timing
                durations.append(duration)
        results[label] = _percentiles(durations)
    return results


def measure_engine_job_durations(iterations: int = 30) -> dict[str, Any]:
    """Measure computational and decision engine execution timings."""
    # 1. Break-even formula: (price_per_unit, variable_cost_per_unit, fixed_costs)
    be_durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        calculate_break_even_quantity(100.0, 40.0, 12000.0)
        be_durations.append(time.perf_counter() - start)

    # 2. Loan amortization schedule (36 months)
    terms = LoanTerms(
        principal=500000.0,
        annual_rate=0.09,
        repayment_months=36,
        moratorium_months=3,
        moratorium_interest_treatment=MoratoriumInterestTreatment.PAID,
        subsidy_amount=50000.0,
        subsidy_treatment=SubsidyTreatment.ADJUSTS_PRINCIPAL,
        subsidy_release_month=None,
    )
    loan_durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        build_loan_schedule(terms)
        loan_durations.append(time.perf_counter() - start)

    # 3. Monte Carlo Decision Risk Simulation (200 draws, PCG64)
    engine = DecisionIntelligenceEngine()
    base_inputs = {
        "machine_name": "CNC Machine",
        "machine_cost": 800000.0,
        "down_payment": 160000.0,
        "loan_amount": 640000.0,
        "loan_interest_rate_pct": 10.5,
        "loan_tenure_months": 36,
        "monthly_maintenance": 5000.0,
        "current_monthly_volume": 1000.0,
        "capacity_monthly_volume": 1500.0,
        "unit_price": 500.0,
        "unit_variable_cost": 300.0,
        "current_cash_liquidity": 350000.0,
        "current_monthly_ebitda": 50000.0,
    }
    uncertainty = {
        "machine_cost": {"std_dev_pct": 0.05},
        "unit_price": {"std_dev_pct": 0.10},
    }
    mc_durations = []
    mc_iterations = max(5, iterations // 3)
    for _ in range(mc_iterations):
        start = time.perf_counter()
        engine.run_monte_carlo_simulation(
            business_id=uuid.uuid4(),
            model_id="MACHINE_OR_EQUIPMENT_PURCHASE",
            base_inputs=base_inputs,
            uncertainty_params=uncertainty,
            iterations=200,
            random_seed=42,
        )
        mc_durations.append(time.perf_counter() - start)

    return {
        "Job: Break-Even Calculation": _percentiles(be_durations),
        "Job: 36-Month Loan Schedule Amortization": _percentiles(loan_durations),
        "Job: Monte Carlo Decision Risk Simulation (200 draws, PCG64)": _percentiles(mc_durations),
    }


def measure_database_query_timings(iterations: int = 30) -> dict[str, Any]:
    """Measure PostgreSQL query response times."""
    engine = get_engine()
    durations = []
    try:
        with engine.connect() as conn:
            for _ in range(iterations):
                start = time.perf_counter()
                conn.execute(text("SELECT 1")).scalar()
                durations.append(time.perf_counter() - start)
    except (SQLAlchemyError, RuntimeError) as exc:
        return {"error": f"Database timing failed: {exc}"}
    return {"Database Query: SELECT 1": _percentiles(durations)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=30, help="Number of measurement trials per target.")
    parser.add_argument("--output", type=Path, default=Path("scripts/system_performance_metrics.json"))
    args = parser.parse_args()

    print(f"Executing ArthLens Business OS latency and job duration benchmarks ({args.iterations} trials)...")
    app = create_app()
    client = TestClient(app)

    api_metrics = measure_api_latencies(client, iterations=args.iterations)
    job_metrics = measure_engine_job_durations(iterations=args.iterations)
    db_metrics = measure_database_query_timings(iterations=args.iterations)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "requested_iterations": args.iterations,
        "api_latencies": {
            "transport": "in_process_asgi_testclient",
            "measurement_note": (
                "In-process Starlette TestClient timings over ASGI memory transport. "
                "Excludes external TCP/IP network latency, load balancer overhead, and TLS termination."
            ),
            "endpoints": api_metrics,
        },
        "job_durations": job_metrics,
        "database_timings": db_metrics,
    }

    rendered = json.dumps(summary, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    print("\n==========================================================================")
    print("      ARTHLENS BUSINESS OS SYSTEM LATENCY & JOB DURATION BENCHMARK        ")
    print("==========================================================================")
    for category, section in [("API Endpoints", api_metrics), ("Computational Jobs", job_metrics), ("Database Operations", db_metrics)]:
        print(f"\n--- {category} ---")
        for name, metrics in section.items():
            if isinstance(metrics, dict) and "p50_ms" in metrics:
                print(f"  {name:42} | p50: {metrics['p50_ms']:>6.2f} ms | p95: {metrics['p95_ms']:>6.2f} ms | max: {metrics['max_ms']:>6.2f} ms")
            else:
                print(f"  {name}: {metrics}")
    print("==========================================================================")
    print(f"Results written to: {args.output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
