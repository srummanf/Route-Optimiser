from __future__ import annotations

import math
import random
from typing import Iterable

DEFAULT_SEED = 81017
DEPOT = (37.7749, -122.4194)


def generate_locations(size: int, seed: int = DEFAULT_SEED) -> list[tuple[float, float]]:
    if size < 2:
        raise ValueError("size must include depot and at least one stop")

    rng = random.Random(seed + size * 9973)
    counts = _band_counts(size - 1)
    locations = [DEPOT]

    for index in range(counts["dense"]):
        locations.append(_cluster_point(rng, index, counts["dense"]))

    for index in range(counts["ring"]):
        locations.append(_ring_point(rng, index, counts["ring"], radius_km=4.2))

    for index in range(counts["outer"]):
        locations.append(_ring_point(rng, index, counts["outer"], radius_km=10.5))

    return [(round(lat, 6), round(lon, 6)) for lat, lon in locations[:size]]


def build_duration_distance_matrices(
    locations: list[tuple[float, float]],
) -> tuple[list[list[int]], list[list[int]]]:
    durations: list[list[int]] = []
    distances: list[list[int]] = []

    for from_index, origin in enumerate(locations):
        duration_row: list[int] = []
        distance_row: list[int] = []

        for to_index, destination in enumerate(locations):
            if from_index == to_index:
                duration_row.append(0)
                distance_row.append(0)
                continue

            distance_m = _haversine_m(origin, destination)
            direction_bias = 1 + (((from_index * 17) + (to_index * 31)) % 9) / 100
            quadrant_bias = 1 + (_quadrant_code(origin, destination) * 0.015)
            band_bias = 1 + abs(_band_index(from_index) - _band_index(to_index)) * 0.03
            adjusted_distance = distance_m * direction_bias * quadrant_bias
            seconds = adjusted_distance / 10.4 * band_bias + ((from_index + to_index) % 13) * 7

            duration_row.append(int(round(seconds)))
            distance_row.append(int(round(adjusted_distance)))

        durations.append(duration_row)
        distances.append(distance_row)

    return durations, distances


def build_route_geometry(
    ordered_locations: list[tuple[float, float]],
) -> tuple[list[list[float]], float, float]:
    if len(ordered_locations) < 2:
        raise ValueError("ordered_locations must contain at least two points")

    coordinates: list[list[float]] = []
    total_distance_m = 0.0
    total_duration_s = 0.0

    for leg_index, (start, end) in enumerate(zip(ordered_locations, ordered_locations[1:])):
        leg_distance = _haversine_m(start, end)
        total_distance_m += leg_distance
        total_duration_s += leg_distance / 11.1 + 14 + (leg_index % 5) * 3

        point_count = max(5, int(leg_distance / 180) + 5)
        leg_points = _interpolate_leg(start, end, point_count, bend_seed=leg_index)

        if coordinates:
            leg_points = leg_points[1:]

        coordinates.extend(leg_points)

    return coordinates, round(total_distance_m, 3), round(total_duration_s, 3)


def serialize_locations(locations: Iterable[tuple[float, float]]) -> list[dict[str, float]]:
    return [{"lat": lat, "lon": lon} for lat, lon in locations]


def _band_counts(stop_count: int) -> dict[str, int]:
    dense = max(1, round(stop_count * 0.5))
    ring = max(1, round(stop_count * 0.3))
    outer = stop_count - dense - ring

    if outer < 1:
        outer = 1
        if dense >= ring:
            dense -= 1
        else:
            ring -= 1

    return {"dense": dense, "ring": ring, "outer": outer}


def _cluster_point(rng: random.Random, index: int, total: int) -> tuple[float, float]:
    angle = (index / max(total, 1)) * math.tau + rng.uniform(-0.15, 0.15)
    radius_km = 0.35 + (index % 5) * 0.18 + rng.uniform(0.0, 0.12)
    return _offset_point(DEPOT, radius_km, angle)


def _ring_point(
    rng: random.Random,
    index: int,
    total: int,
    radius_km: float,
) -> tuple[float, float]:
    angle = ((index + 1) / (total + 1)) * math.tau + rng.uniform(-0.1, 0.1)
    band_radius = radius_km + ((index % 4) - 1.5) * 0.5 + rng.uniform(-0.2, 0.2)
    return _offset_point(DEPOT, band_radius, angle)


def _offset_point(
    point: tuple[float, float],
    radius_km: float,
    angle: float,
) -> tuple[float, float]:
    lat, lon = point
    lat_delta = (radius_km / 111.0) * math.cos(angle)
    lon_delta = (radius_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(angle)
    return lat + lat_delta, lon + lon_delta


def _interpolate_leg(
    start: tuple[float, float],
    end: tuple[float, float],
    point_count: int,
    bend_seed: int,
) -> list[list[float]]:
    start_lat, start_lon = start
    end_lat, end_lon = end
    lat_mid = (start_lat + end_lat) / 2
    lon_mid = (start_lon + end_lon) / 2
    lat_delta = end_lat - start_lat
    lon_delta = end_lon - start_lon
    length = math.hypot(lat_delta, lon_delta)
    bend_scale = 0.06 + (bend_seed % 7) * 0.01
    bend_lat = lat_mid + (-lon_delta * bend_scale)
    bend_lon = lon_mid + (lat_delta * bend_scale)

    points: list[list[float]] = []

    for index in range(point_count):
        t = index / (point_count - 1)
        one_minus_t = 1 - t
        lat = (
            one_minus_t * one_minus_t * start_lat
            + 2 * one_minus_t * t * bend_lat
            + t * t * end_lat
        )
        lon = (
            one_minus_t * one_minus_t * start_lon
            + 2 * one_minus_t * t * bend_lon
            + t * t * end_lon
        )
        wave = math.sin(t * math.pi) * length * 0.08
        points.append([round(lon + wave, 6), round(lat - wave, 6)])

    return points


def _haversine_m(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, origin)
    lat2, lon2 = map(math.radians, destination)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _quadrant_code(origin: tuple[float, float], destination: tuple[float, float]) -> int:
    lat1, lon1 = origin
    lat2, lon2 = destination
    code = 0
    if lat2 >= lat1:
        code += 1
    if lon2 >= lon1:
        code += 1
    return code


def _band_index(node_index: int) -> int:
    if node_index == 0:
        return 0
    if node_index <= 40:
        return 1
    if node_index <= 80:
        return 2
    return 3
