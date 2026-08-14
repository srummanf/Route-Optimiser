# Route Size Benchmark

Run the benchmark from the repository root:

```bash
python -m backend.benchmarks.route_size_benchmark
```

Optional flags:

```bash
python -m backend.benchmarks.route_size_benchmark \
  --output-dir backend/benchmarks/results \
  --warmups 1 \
  --repetitions 5 \
  --baseline-time-limit 45 \
  --recompute-baselines
```

Artifacts written to the output directory:

- `raw_runs.csv`
- `summary.json`
- `baseline_objectives.json`
- `coordinates.json`
- `route-size-envelope-report.md`

Notes:

- The benchmark imports the current production `build_duration_matrix`, `solve_route`, and `get_route_geometry` functions directly.
- OSRM traffic is redirected to a localhost fake fixture at runtime only; production modules are not edited.
- The benchmark records separate findings for Table, Solver, and Geometry instead of timing the FastAPI endpoint end to end.
