# Route Size Envelope Report

## Summary
- Recommended default maximum: **5** locations including depot.
- Largest passing tested size: **none**.
- Decision basis: provisional fallback because no size passed every hard threshold.
- First failing sizes: table=None, solver=5, geometry=None.

## Environment
- Run date: 2026-08-14T04:31:36.122319+00:00
- Python: 3.11.2
- Platform: Linux-6.1.102-x86_64-with-glibc2.36
- Fixture mode: localhost fake OSRM at http://127.0.0.1:36155
- Random seed: 81017
- Measured repetitions: 3
- Warm-up repetitions: 1
- Baseline method: exact permutation for sizes 5 and 10; extended OR-Tools for 20, 40, 80, and 120 with 20 second limit.
- public_network_used: false

## Methodology
- Deterministic depot-first coordinate sets with dense, ring, and outer-ring patterns.
- Table metrics measure URL bytes, fixture latency, response bytes, and matrix dimensions.
- Solver metrics measure solve latency, timeout/no-solution count, route objective, and quality gap against stored baselines.
- Geometry metrics measure URL bytes, fixture latency, response bytes, and coordinate count for the returned GeoJSON line.
- Percentiles use nearest-rank over measured samples after warm-ups.

## Table Results

| Size | p50 ms | p95 ms | max ms | URL max bytes | Response max bytes | Extra | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 5 | 3.784 | 4.648 | 4.648 | 174.0 | 261.0 | count=3 | PASS |
| 10 | 1.561 | 2.924 | 2.924 | 283.0 | 954.0 | count=3 | PASS |
| 20 | 6.645 | 7.117 | 7.117 | 499.0 | 3725.0 | count=3 | PASS |
| 40 | 8.102 | 8.428 | 8.428 | 939.0 | 14944.0 | count=3 | PASS |
| 80 | 20.265 | 20.587 | 20.587 | 1811.0 | 59955.0 | count=3 | PASS |
| 120 | 45.993 | 48.585 | 48.585 | 2681.0 | 135213.0 | count=3 | PASS |

## Solver Results

| Size | p50 ms | p95 ms | max ms | URL max bytes | Response max bytes | Extra | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 5 | 30007.505 | 30008.885 | 30008.885 | - | - | none=0, objective p50=2153.0, gap p50=0.0% | FAIL |
| 10 | 30001.238 | 30012.023 | 30012.023 | - | - | none=0, objective p50=4311.0, gap p50=0.0% | FAIL |
| 20 | 30003.826 | 30004.084 | 30004.084 | - | - | none=0, objective p50=6778.0, gap p50=0.0% | FAIL |
| 40 | 30001.85 | 30003.201 | 30003.201 | - | - | none=0, objective p50=11327.0, gap p50=0.0% | FAIL |
| 80 | 30001.921 | 30002.879 | 30002.879 | - | - | none=0, objective p50=14522.0, gap p50=0.0% | FAIL |
| 120 | 30003.123 | 30009.149 | 30009.149 | - | - | none=0, objective p50=17259.0, gap p50=-0.093% | FAIL |

## Geometry Results

| Size | p50 ms | p95 ms | max ms | URL max bytes | Response max bytes | Extra | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 5 | 4.292 | 5.529 | 5.529 | 207.0 | 3224.0 | coords max=131.0 | PASS |
| 10 | 3.772 | 6.407 | 6.407 | 316.0 | 6317.0 | coords max=261.0 | PASS |
| 20 | 4.713 | 5.02 | 5.02 | 532.0 | 9828.0 | coords max=409.0 | PASS |
| 40 | 8.611 | 9.693 | 9.693 | 972.0 | 16203.0 | coords max=677.0 | PASS |
| 80 | 9.415 | 11.303 | 11.303 | 1844.0 | 22898.0 | coords max=958.0 | PASS |
| 120 | 9.463 | 13.443 | 13.443 | 2714.0 | 28881.0 | coords max=1210.0 | PASS |

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
- Production modules `backend/app.py`, `backend/osrm_service.py`, and `backend/solver.py` were left unchanged.
- Benchmark requests targeted localhost only through a runtime `OSRM_BASE_URL` override.
- The benchmark records `public_network_used=false` only when every fixture request stayed on `127.0.0.1`.
