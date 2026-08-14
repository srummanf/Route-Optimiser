from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import datetime as dt
import io
import json
import os
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

import osrm_service  # noqa: E402
from solver import solve_route  # noqa: E402

from backend.benchmarks.baselines import ensure_baseline, load_baselines, route_objective, save_baselines
from backend.benchmarks.datasets import DEFAULT_SEED, generate_locations, serialize_locations
from backend.benchmarks.fake_osrm import FakeOSRMFixture
from backend.benchmarks.reporting import aggregate_runs, choose_default_maximum, evaluate_thresholds, write_report, write_summary

SIZES = [5, 10, 20, 40, 80, 120]
DEFAULT_OUTPUT_DIR = ROOT / "backend" / "benchmarks" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local OSRM/OR-Tools route-size benchmark")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--baseline-time-limit", type=int, default=45)
    parser.add_argument("--fixture-port", type=int, default=0)
    parser.add_argument("--recompute-baselines", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    solver_time_limit_seconds = read_solver_time_limit_seconds(ROOT / "backend" / "solver.py")
    effective_baseline_time_limit = max(args.baseline_time_limit, solver_time_limit_seconds)
    module_hashes_before = production_module_hashes()

    fixture = FakeOSRMFixture(port=args.fixture_port)
    fixture.start()
    original_base_url = osrm_service.OSRM_BASE_URL
    osrm_service.OSRM_BASE_URL = fixture.base_url

    if "router.project-osrm.org" in osrm_service.OSRM_BASE_URL:
        raise RuntimeError("benchmark setup failed to override OSRM host")

    try:
        verify_fixture_contract(fixture)
        verify_dataset_determinism(args.seed)

        baselines_path = output_dir / "baseline_objectives.json"
        baselines = {} if args.recompute_baselines else load_baselines(baselines_path)

        raw_rows: list[dict] = []
        coordinates_payload: dict[str, list[dict[str, float]]] = {}

        for size in SIZES:
            print(f"running size {size}", flush=True)
            locations = generate_locations(size, seed=args.seed)
            coordinates_payload[str(size)] = serialize_locations(locations)
            raw_rows.extend(
                run_size(
                    size=size,
                    locations=locations,
                    fixture=fixture,
                    baselines=baselines,
                    warmups=args.warmups,
                    repetitions=args.repetitions,
                    baseline_time_limit=effective_baseline_time_limit,
                )
            )

        save_baselines(baselines_path, baselines)
        write_coordinates(output_dir / "coordinates.json", coordinates_payload)
        write_raw_runs(output_dir / "raw_runs.csv", raw_rows)
        module_hashes_after = production_module_hashes()
        if module_hashes_after != module_hashes_before:
            raise RuntimeError("production module contents changed during benchmark execution")

        summary = aggregate_runs(raw_rows)
        decisions = evaluate_thresholds(summary)
        recommendation = choose_default_maximum(summary, decisions, solver_time_limit_seconds)
        context = {
            "run_date": dt.datetime.now(dt.timezone.utc).isoformat(),
            "fixture_base_url": fixture.base_url,
            "seed": args.seed,
            "warmup_repetitions": args.warmups,
            "measured_repetitions": args.repetitions,
            "baseline_time_limit_seconds": effective_baseline_time_limit,
            "requested_baseline_time_limit_seconds": args.baseline_time_limit,
            "solver_time_limit_seconds": solver_time_limit_seconds,
            "public_network_used": not fixture.metrics.all_localhost(),
            "production_modules_unchanged": True,
            "production_module_hashes": module_hashes_after,
        }
        summary_payload = {
            "context": context,
            "summary": summary,
            "decisions": decisions,
            "recommendation": recommendation,
        }
        write_summary(output_dir / "summary.json", summary_payload)
        report_path = write_report(output_dir, context, summary, decisions, recommendation)
        verify_report(report_path)
        return 0
    finally:
        osrm_service.OSRM_BASE_URL = original_base_url
        fixture.stop()


def run_size(
    size: int,
    locations: list[tuple[float, float]],
    fixture: FakeOSRMFixture,
    baselines: dict[str, dict],
    warmups: int,
    repetitions: int,
    baseline_time_limit: int,
) -> list[dict]:
    rows: list[dict] = []
    warmup_total = warmups + repetitions

    for iteration in range(warmup_total):
        is_warmup = iteration < warmups
        table_row, durations = measure_table(size, iteration, is_warmup, locations, fixture)
        baseline = ensure_baseline(baselines, size, durations, baseline_time_limit)
        solver_row, visit_order = measure_solver(size, iteration, is_warmup, durations, baseline)
        geometry_row = measure_geometry(size, iteration, is_warmup, locations, visit_order, fixture)

        if not is_warmup:
            rows.append(table_row)
            rows.append(solver_row)
            rows.append(geometry_row)

    return rows


def measure_table(
    size: int,
    iteration: int,
    is_warmup: bool,
    locations: list[tuple[float, float]],
    fixture: FakeOSRMFixture,
) -> tuple[dict, list[list[int]]]:
    started = time.perf_counter_ns()
    durations, distances = osrm_service.build_duration_matrix(locations)
    elapsed_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)
    metrics = fixture.metrics.pop_latest("table")

    coordinates = ";".join(f"{lon},{lat}" for lat, lon in locations)
    url = (
        f"{osrm_service.OSRM_BASE_URL}/table/v1/driving/{coordinates}"
        "?annotations=duration,distance"
    )

    row = {
        "size": size,
        "phase": "table",
        "iteration": iteration,
        "warmup": is_warmup,
        "elapsed_ms": elapsed_ms,
        "fixture_service_ms": metrics["service_time_ms"],
        "url_bytes": len(url.encode("utf-8")),
        "response_bytes": metrics["response_bytes"],
        "location_count": metrics["location_count"],
        "matrix_dimension": len(durations),
        "distance_matrix_dimension": len(distances),
        "status": "ok",
    }
    return row, durations


def measure_solver(
    size: int,
    iteration: int,
    is_warmup: bool,
    duration_matrix: list[list[int]],
    baseline: dict,
) -> tuple[dict, list[int] | None]:
    started = time.perf_counter_ns()
    with muted_output():
        visit_order = solve_route(duration_matrix)
    elapsed_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)

    if visit_order is None:
        row = {
            "size": size,
            "phase": "solver",
            "iteration": iteration,
            "warmup": is_warmup,
            "elapsed_ms": elapsed_ms,
            "objective_value": None,
            "baseline_objective": baseline["objective"],
            "quality_gap_pct": 100.0,
            "status": "no_solution",
        }
        return row, None

    objective = route_objective(duration_matrix, visit_order)
    quality_gap = round(((objective - baseline["objective"]) / baseline["objective"]) * 100, 3)
    row = {
        "size": size,
        "phase": "solver",
        "iteration": iteration,
        "warmup": is_warmup,
        "elapsed_ms": elapsed_ms,
        "objective_value": objective,
        "baseline_objective": baseline["objective"],
        "quality_gap_pct": quality_gap,
        "status": "ok",
    }
    return row, visit_order


def measure_geometry(
    size: int,
    iteration: int,
    is_warmup: bool,
    locations: list[tuple[float, float]],
    visit_order: list[int] | None,
    fixture: FakeOSRMFixture,
) -> dict:
    if visit_order is None:
        return {
            "size": size,
            "phase": "geometry",
            "iteration": iteration,
            "warmup": is_warmup,
            "elapsed_ms": None,
            "fixture_service_ms": None,
            "url_bytes": None,
            "response_bytes": None,
            "geometry_coordinate_count": None,
            "status": "skipped",
        }

    started = time.perf_counter_ns()
    route = osrm_service.get_route_geometry(locations, visit_order)
    elapsed_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)
    metrics = fixture.metrics.pop_latest("route")

    ordered = [locations[index] for index in visit_order]
    coordinates = ";".join(f"{lon},{lat}" for lat, lon in ordered)
    url = (
        f"{osrm_service.OSRM_BASE_URL}/route/v1/driving/{coordinates}"
        "?overview=full&geometries=geojson&steps=false"
    )

    return {
        "size": size,
        "phase": "geometry",
        "iteration": iteration,
        "warmup": is_warmup,
        "elapsed_ms": elapsed_ms,
        "fixture_service_ms": metrics["service_time_ms"],
        "url_bytes": len(url.encode("utf-8")),
        "response_bytes": metrics["response_bytes"],
        "geometry_coordinate_count": len(route["geometry"]),
        "status": "ok",
    }


def verify_fixture_contract(fixture: FakeOSRMFixture) -> None:
    sample_locations = generate_locations(5)
    durations, distances = osrm_service.build_duration_matrix(sample_locations)
    if len(durations) != 5 or len(distances) != 5:
        raise RuntimeError("fixture table contract returned invalid matrix dimensions")
    fixture.metrics.pop_latest("table")

    route = osrm_service.get_route_geometry(sample_locations, [0, 1, 2, 3, 4, 0])
    if not route["geometry"]:
        raise RuntimeError("fixture route contract returned empty geometry")
    fixture.metrics.pop_latest("route")


def verify_dataset_determinism(seed: int) -> None:
    first = generate_locations(20, seed=seed)
    second = generate_locations(20, seed=seed)
    if first != second:
        raise RuntimeError("dataset generator is not deterministic")


def verify_report(report_path: Path) -> None:
    content = report_path.read_text(encoding="utf-8")
    required = [
        "## Table Results",
        "## Solver Results",
        "## Geometry Results",
        "## Evidence Checks",
        "Recommended default maximum",
        "public_network_used: false",
    ]
    for token in required:
        if token not in content:
            raise RuntimeError(f"report missing expected content: {token}")


def write_coordinates(path: Path, payload: dict[str, list[dict[str, float]]]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_raw_runs(path: Path, rows: list[dict]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_solver_time_limit_seconds(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Attribute) or target.attr != "seconds":
            continue
        time_limit = target.value
        if not isinstance(time_limit, ast.Attribute) or time_limit.attr != "time_limit":
            continue
        owner = time_limit.value
        if not isinstance(owner, ast.Name) or owner.id != "search_parameters":
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, int):
            raise RuntimeError("solver time limit is not an integer literal")
        return node.value.value
    raise RuntimeError("could not locate solver time limit in backend/solver.py")


def production_module_hashes() -> dict[str, str]:
    files = [
        ROOT / "backend" / "app.py",
        ROOT / "backend" / "osrm_service.py",
        ROOT / "backend" / "solver.py",
    ]
    return {path.name: sha256_file(path) for path in files}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextlib.contextmanager
def muted_output():
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            stdout_fd = os.dup(1)
            stderr_fd = os.dup(2)
            try:
                os.dup2(devnull.fileno(), 1)
                os.dup2(devnull.fileno(), 2)
                yield
            finally:
                os.dup2(stdout_fd, 1)
                os.dup2(stderr_fd, 2)
                os.close(stdout_fd)
                os.close(stderr_fd)


if __name__ == "__main__":
    raise SystemExit(main())
