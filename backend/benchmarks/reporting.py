from __future__ import annotations

import json
import math
import platform
import statistics
from collections import defaultdict
from pathlib import Path


TABLE_URL_LIMIT_BYTES = 7500
TABLE_P95_LIMIT_MS = 2000
SOLVER_P95_LIMIT_MS = 25000
SOLVER_QUALITY_GAP_LIMIT_PCT = 5.0
GEOMETRY_RESPONSE_LIMIT_BYTES = 5 * 1024 * 1024
GEOMETRY_COORD_LIMIT = 50000
GEOMETRY_P95_LIMIT_MS = 3000


def aggregate_runs(raw_rows: list[dict]) -> dict[str, dict[str, dict]]:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in raw_rows:
        if row["phase"] == "geometry" and row.get("status") == "skipped":
            continue
        grouped[str(row["size"])][row["phase"]].append(row)

    summary: dict[str, dict[str, dict]] = {}
    for size, phases in grouped.items():
        summary[size] = {}
        for phase, rows in phases.items():
            elapsed = [row["elapsed_ms"] for row in rows]
            phase_summary = {
                "count": len(rows),
                "min_ms": round(min(elapsed), 3),
                "mean_ms": round(statistics.fmean(elapsed), 3),
                "p50_ms": percentile_nearest_rank(elapsed, 50),
                "p95_ms": percentile_nearest_rank(elapsed, 95),
                "max_ms": round(max(elapsed), 3),
            }

            if phase in {"table", "geometry"}:
                phase_summary["url_bytes"] = summarize_numeric(rows, "url_bytes")
                phase_summary["response_bytes"] = summarize_numeric(rows, "response_bytes")
            if phase == "geometry":
                phase_summary["geometry_coordinate_count"] = summarize_numeric(
                    rows, "geometry_coordinate_count"
                )
            if phase == "solver":
                phase_summary["objective"] = summarize_numeric(rows, "objective_value")
                phase_summary["quality_gap_pct"] = summarize_numeric(rows, "quality_gap_pct")
                phase_summary["none_count"] = sum(1 for row in rows if row["status"] == "no_solution")

            summary[size][phase] = phase_summary
    return summary


def evaluate_thresholds(summary: dict[str, dict[str, dict]]) -> dict[str, dict]:
    decisions: dict[str, dict] = {}
    for size_str, phases in summary.items():
        table = phases["table"]
        solver = phases["solver"]
        geometry = phases.get("geometry", {})

        table_pass = (
            table["url_bytes"]["max"] <= TABLE_URL_LIMIT_BYTES
            and table["p95_ms"] <= TABLE_P95_LIMIT_MS
        )
        solver_pass = (
            solver["none_count"] == 0
            and solver["p95_ms"] <= SOLVER_P95_LIMIT_MS
            and solver["quality_gap_pct"]["p50"] <= SOLVER_QUALITY_GAP_LIMIT_PCT
        )
        geometry_pass = (
            geometry["response_bytes"]["max"] <= GEOMETRY_RESPONSE_LIMIT_BYTES
            and geometry["geometry_coordinate_count"]["max"] <= GEOMETRY_COORD_LIMIT
            and geometry["p95_ms"] <= GEOMETRY_P95_LIMIT_MS
        )

        decisions[size_str] = {
            "table_pass": table_pass,
            "solver_pass": solver_pass,
            "geometry_pass": geometry_pass,
            "all_pass": table_pass and solver_pass and geometry_pass,
            "threshold_margin_pct": round(
                min(
                    margin_pct(TABLE_URL_LIMIT_BYTES, table["url_bytes"]["max"]),
                    margin_pct(TABLE_P95_LIMIT_MS, table["p95_ms"]),
                    margin_pct(SOLVER_P95_LIMIT_MS, solver["p95_ms"]),
                    margin_pct(
                        SOLVER_QUALITY_GAP_LIMIT_PCT,
                        solver["quality_gap_pct"]["p50"],
                        invert=True,
                    ),
                    margin_pct(
                        GEOMETRY_RESPONSE_LIMIT_BYTES,
                        geometry["response_bytes"]["max"],
                    ),
                    margin_pct(
                        GEOMETRY_COORD_LIMIT,
                        geometry["geometry_coordinate_count"]["max"],
                    ),
                    margin_pct(GEOMETRY_P95_LIMIT_MS, geometry["p95_ms"]),
                ),
                3,
            ),
        }
    return decisions


def choose_default_maximum(summary: dict[str, dict[str, dict]], decisions: dict[str, dict]) -> dict:
    sizes = sorted(int(size) for size in summary)
    passing = [size for size in sizes if decisions[str(size)]["all_pass"]]

    if passing:
        winner = max(passing)
        margin = decisions[str(winner)]["threshold_margin_pct"]
        recommended = winner
        if margin <= 15:
            winner_index = sizes.index(winner)
            if winner_index > 0:
                recommended = sizes[winner_index - 1]
        rationale = (
            "largest passing size"
            if recommended == winner
            else "one-step safety margin from the largest passing size"
        )
        provisional = False
    else:
        candidates = [
            size
            for size in sizes
            if summary[str(size)]["solver"]["p50_ms"] < SOLVER_P95_LIMIT_MS
        ]
        recommended = max(candidates) if candidates else min(sizes)
        winner = None
        rationale = "provisional fallback because no size passed every hard threshold"
        provisional = True

    return {
        "recommended_default_maximum": recommended,
        "largest_passing_size": winner,
        "rationale": rationale,
        "provisional": provisional,
        "first_failing_table_size": first_failing_size(decisions, "table_pass"),
        "first_failing_solver_size": first_failing_size(decisions, "solver_pass"),
        "first_failing_geometry_size": first_failing_size(decisions, "geometry_pass"),
    }


def write_summary(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_report(
    output_dir: Path,
    context: dict,
    summary: dict[str, dict[str, dict]],
    decisions: dict[str, dict],
    recommendation: dict,
) -> Path:
    report_path = output_dir / "route-size-envelope-report.md"
    lines = [
        "# Route Size Envelope Report",
        "",
        "## Summary",
        (
            f"- Recommended default maximum: **{recommendation['recommended_default_maximum']}** "
            "locations including depot."
        ),
        (
            f"- Largest passing tested size: "
            f"**{recommendation['largest_passing_size'] or 'none'}**."
        ),
        f"- Decision basis: {recommendation['rationale']}.",
        (
            f"- First failing sizes: table={recommendation['first_failing_table_size']}, "
            f"solver={recommendation['first_failing_solver_size']}, "
            f"geometry={recommendation['first_failing_geometry_size']}."
        ),
        "",
        "## Environment",
        f"- Run date: {context['run_date']}",
        f"- Python: {platform.python_version()}",
        f"- Platform: {platform.platform()}",
        f"- Fixture mode: localhost fake OSRM at {context['fixture_base_url']}",
        f"- Random seed: {context['seed']}",
        f"- Measured repetitions: {context['measured_repetitions']}",
        f"- Warm-up repetitions: {context['warmup_repetitions']}",
        (
            f"- Baseline method: exact permutation for sizes 5 and 10; "
            f"extended OR-Tools for 20, 40, 80, and 120 with "
            f"{context['baseline_time_limit_seconds']} second limit."
        ),
        f"- public_network_used: {str(context['public_network_used']).lower()}",
        "",
        "## Methodology",
        "- Deterministic depot-first coordinate sets with dense, ring, and outer-ring patterns.",
        "- Table metrics measure URL bytes, fixture latency, response bytes, and matrix dimensions.",
        "- Solver metrics measure solve latency, timeout/no-solution count, route objective, and quality gap against stored baselines.",
        "- Geometry metrics measure URL bytes, fixture latency, response bytes, and coordinate count for the returned GeoJSON line.",
        "- Percentiles use nearest-rank over measured samples after warm-ups.",
        "",
    ]

    for phase_name, title in (("table", "Table"), ("solver", "Solver"), ("geometry", "Geometry")):
        lines.append(f"## {title} Results")
        lines.append("")
        lines.append(
            "| Size | p50 ms | p95 ms | max ms | URL max bytes | Response max bytes | Extra | Pass |"
        )
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |")

        for size in sorted(int(value) for value in summary):
            phase = summary[str(size)][phase_name]
            decision = decisions[str(size)]
            if phase_name == "solver":
                extra = (
                    f"none={phase['none_count']}, "
                    f"objective p50={phase['objective']['p50']}, "
                    f"gap p50={phase['quality_gap_pct']['p50']}%"
                )
                url_max = "-"
                response_max = "-"
                passed = decision["solver_pass"]
            elif phase_name == "geometry":
                extra = f"coords max={phase['geometry_coordinate_count']['max']}"
                url_max = phase["url_bytes"]["max"]
                response_max = phase["response_bytes"]["max"]
                passed = decision["geometry_pass"]
            else:
                extra = f"count={phase['count']}"
                url_max = phase["url_bytes"]["max"]
                response_max = phase["response_bytes"]["max"]
                passed = decision["table_pass"]

            lines.append(
                f"| {size} | {phase['p50_ms']} | {phase['p95_ms']} | {phase['max_ms']} | "
                f"{url_max} | {response_max} | {extra} | {'PASS' if passed else 'FAIL'} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Threshold Interpretation",
            "",
            f"- Table hard thresholds: URL <= {TABLE_URL_LIMIT_BYTES} bytes and p95 <= {TABLE_P95_LIMIT_MS} ms.",
            (
                f"- Solver hard thresholds: no `None` results, p95 <= {SOLVER_P95_LIMIT_MS} ms, "
                f"median quality gap <= {SOLVER_QUALITY_GAP_LIMIT_PCT}%."
            ),
            (
                f"- Geometry hard thresholds: response <= {GEOMETRY_RESPONSE_LIMIT_BYTES} bytes, "
                f"coordinates <= {GEOMETRY_COORD_LIMIT}, p95 <= {GEOMETRY_P95_LIMIT_MS} ms."
            ),
            "",
            "## Artifact Inventory",
            "- `raw_runs.csv`",
            "- `summary.json`",
            "- `baseline_objectives.json`",
            "- `coordinates.json`",
            "- `route-size-envelope-report.md`",
            "",
            "## Safeguards",
            "- Production modules `backend/app.py`, `backend/osrm_service.py`, and `backend/solver.py` were left unchanged.",
            "- Benchmark requests targeted localhost only through a runtime `OSRM_BASE_URL` override.",
            "- The benchmark records `public_network_used=false` only when every fixture request stayed on `127.0.0.1`.",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def summarize_numeric(rows: list[dict], key: str) -> dict[str, float]:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return {
        "min": round(min(values), 3),
        "p50": percentile_nearest_rank(values, 50),
        "p95": percentile_nearest_rank(values, 95),
        "max": round(max(values), 3),
    }


def percentile_nearest_rank(values: list[float], percentile: int) -> float:
    sorted_values = sorted(values)
    rank = max(1, math.ceil((percentile / 100) * len(sorted_values)))
    return round(sorted_values[rank - 1], 3)


def first_failing_size(decisions: dict[str, dict], field: str) -> int | None:
    for size in sorted(int(size_str) for size_str in decisions):
        if not decisions[str(size)][field]:
            return size
    return None


def margin_pct(limit: float, value: float, invert: bool = False) -> float:
    if limit == 0:
        return 0.0
    if invert:
        return ((limit - value) / limit) * 100
    return ((limit - value) / limit) * 100
