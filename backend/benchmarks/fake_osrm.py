from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .datasets import build_duration_distance_matrices, build_route_geometry


@dataclass
class FixtureMetricsStore:
    requests: list[dict] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)

    def record(self, payload: dict) -> None:
        self.requests.append(payload)
        self.history.append(payload)

    def pop_latest(self, kind: str) -> dict:
        for index in range(len(self.requests) - 1, -1, -1):
            record = self.requests[index]
            if record["kind"] == kind:
                return self.requests.pop(index)
        raise RuntimeError(f"no recorded fixture request for kind={kind}")

    def all_localhost(self) -> bool:
        return bool(self.history) and all(record["host"] == "127.0.0.1" for record in self.history)


class FakeOSRMFixture:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.metrics = FixtureMetricsStore()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("fixture is not running")
        return f"http://{self.host}:{self._server.server_port}"

    def start(self) -> None:
        metrics = self.metrics

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                started = time.perf_counter_ns()
                path_only = self.path.split("?", 1)[0]
                segments = [segment for segment in path_only.split("/") if segment]

                if len(segments) < 4 or segments[0] not in {"table", "route"}:
                    self.send_error(404)
                    return

                kind = segments[0]
                coord_blob = segments[3]
                locations = _parse_coordinates(coord_blob)

                if kind == "table":
                    durations, distances = build_duration_distance_matrices(locations)
                    payload = {
                        "code": "Ok",
                        "durations": durations,
                        "distances": distances,
                    }
                else:
                    geometry, distance_m, duration_s = build_route_geometry(locations)
                    payload = {
                        "code": "Ok",
                        "routes": [
                            {
                                "distance": distance_m,
                                "duration": duration_s,
                                "geometry": {"coordinates": geometry, "type": "LineString"},
                            }
                        ],
                    }

                body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000

                metrics.record(
                    {
                        "kind": kind,
                        "host": self.server.server_address[0],
                        "path_bytes": len(self.path.encode("utf-8")),
                        "response_bytes": len(body),
                        "location_count": len(locations),
                        "service_time_ms": round(elapsed_ms, 3),
                        "geometry_coordinate_count": (
                            len(payload["routes"][0]["geometry"]["coordinates"])
                            if kind == "route"
                            else None
                        ),
                    }
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt: str, *args) -> None:
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None


def _parse_coordinates(coord_blob: str) -> list[tuple[float, float]]:
    locations = []
    for raw in coord_blob.split(";"):
        lon, lat = raw.split(",")
        locations.append((float(lat), float(lon)))
    return locations
