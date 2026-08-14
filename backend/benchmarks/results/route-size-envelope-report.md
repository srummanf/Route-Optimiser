# Route Size Envelope Report

## Summary
- Recommended default maximum: **5** locations including depot.
- Largest passing tested size: **none**.
- Decision basis: provisional fallback because no size passed every hard threshold.
- First failing sizes: table=None, solver=5, geometry=None.

## Environment
- Run date: 2026-08-14T04:49:54.253058+00:00
- Python: 3.11.2
- Platform: Linux-6.1.102-x86_64-with-glibc2.36
- Fixture mode: localhost fake OSRM at http://127.0.0.1:46623
- Random seed: 81017
- Measured repetitions: 3
- Warm-up repetitions: 1
- Solver configured time limit: 30 seconds from `backend/solver.py`.
- Baseline method: exact permutation for sizes 5 and 10; extended OR-Tools for 20, 40, 80, and 120 with 30 second limit.
- Requested baseline time limit: 30 seconds.
- public_network_used: false

## Methodology
- Deterministic depot-first coordinate sets with dense, ring, and outer-ring patterns.
- Table metrics measure URL bytes, fixture latency, response bytes, and matrix dimensions.
- Solver metrics measure the full `solve_route()` call, timeout/no-solution count, route objective, and quality gap against stored baselines.
- Geometry metrics measure URL bytes, fixture latency, response bytes, and coordinate count for the returned GeoJSON line.
- Percentiles use nearest-rank over measured samples after warm-ups.
- Benchmark imports production `build_duration_matrix()`, `solve_route()`, and `get_route_geometry()` directly, overriding only `OSRM_BASE_URL` at runtime.

## Table Results

| Size | p50 ms | p95 ms | max ms | URL max bytes | Response max bytes | Extra | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 5 | 1.465 | 1.541 | 1.541 | 174.0 | 261.0 | count=3 | PASS |
| 10 | 1.446 | 1.489 | 1.489 | 283.0 | 954.0 | count=3 | PASS |
| 20 | 1.963 | 2.239 | 2.239 | 499.0 | 3725.0 | count=3 | PASS |
| 40 | 3.843 | 3.865 | 3.865 | 939.0 | 14944.0 | count=3 | PASS |
| 80 | 10.923 | 11.631 | 11.631 | 1811.0 | 59955.0 | count=3 | PASS |
| 120 | 21.804 | 22.132 | 22.132 | 2681.0 | 135213.0 | count=3 | PASS |

## Solver Results

| Size | p50 ms | p95 ms | max ms | URL max bytes | Response max bytes | Extra | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 5 | 30001.193 | 30001.199 | 30001.199 | - | - | none=0, objective p50=2153.0, gap p50=0.0% | FAIL |
| 10 | 30001.294 | 30001.359 | 30001.359 | - | - | none=0, objective p50=4311.0, gap p50=0.0% | FAIL |
| 20 | 30001.424 | 30001.615 | 30001.615 | - | - | none=0, objective p50=6778.0, gap p50=0.0% | FAIL |
| 40 | 30001.535 | 30001.55 | 30001.55 | - | - | none=0, objective p50=11327.0, gap p50=0.0% | FAIL |
| 80 | 30002.038 | 30002.492 | 30002.492 | - | - | none=0, objective p50=14505.0, gap p50=0.014% | FAIL |
| 120 | 30001.278 | 30001.286 | 30001.286 | - | - | none=0, objective p50=17154.0, gap p50=0.175% | FAIL |

## Geometry Results

| Size | p50 ms | p95 ms | max ms | URL max bytes | Response max bytes | Extra | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 5 | 2.256 | 2.483 | 2.483 | 207.0 | 3224.0 | coords max=131.0 | PASS |
| 10 | 2.395 | 2.418 | 2.418 | 316.0 | 6317.0 | coords max=261.0 | PASS |
| 20 | 2.791 | 2.804 | 2.804 | 532.0 | 9828.0 | coords max=409.0 | PASS |
| 40 | 3.37 | 3.783 | 3.783 | 972.0 | 16203.0 | coords max=677.0 | PASS |
| 80 | 4.82 | 5.217 | 5.217 | 1844.0 | 22993.0 | coords max=962.0 | PASS |
| 120 | 5.118 | 5.135 | 5.135 | 2714.0 | 28630.0 | coords max=1199.0 | PASS |

## Threshold Interpretation

- Table hard thresholds: URL <= 7500 bytes and p95 <= 2000 ms.
- Solver hard thresholds: no `None` results, p95 <= 25000 ms, median quality gap <= 5.0%.
- Geometry hard thresholds: response <= 5242880 bytes, coordinates <= 50000, p95 <= 3000 ms.

## Artifact Inventory
- `raw_runs.csv`
- `summary.json`
- `baseline_objectives.json`
- `coordinates.json`
- `route-size-envelope-report.md`

## Safeguards
- Production modules `backend/app.py`, `backend/osrm_service.py`, and `backend/solver.py` were executed directly rather than copied into benchmark-specific shims.
- Benchmark requests targeted localhost only through a runtime `OSRM_BASE_URL` override.
- The benchmark records `public_network_used=false` only when every fixture request stayed on `127.0.0.1`.

## Evidence Checks

- Baseline validity: sizes 5 and 10 use exact permutation; larger sizes use cached OR-Tools baselines only when their recorded time limit is at least the measured solver budget. Current baseline limit: 30 seconds.
- Solver accounting: any solver p50/p95 near 30000 ms indicates the production solver consumed essentially its full configured search budget.
- Production behavior unchanged: pre/post SHA-256 digests matched for `backend/app.py`, `backend/osrm_service.py`, and `backend/solver.py`.
- Production module digests: {"app.py": "7a9d8405ddfd062f1410e3104158948b06c7a3c7e5825b89869aa2cfdde56aa7", "osrm_service.py": "036154b83037d75dac35e1e9eea843e381db968511efeb63eaf5fa6394b440ad", "solver.py": "d00f3409b85817db272a74d9cc687d6a80594780b925167f60cfb9f4f1789f19"}
