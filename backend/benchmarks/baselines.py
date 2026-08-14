from __future__ import annotations

import itertools
import json
from pathlib import Path

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2


def load_baselines(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_baselines(path: Path, baselines: dict[str, dict]) -> None:
    path.write_text(json.dumps(baselines, indent=2, sort_keys=True), encoding="utf-8")


def ensure_baseline(
    baselines: dict[str, dict],
    size: int,
    duration_matrix: list[list[int]],
    time_limit_seconds: int,
) -> dict:
    key = str(size)
    if key in baselines:
        return baselines[key]

    if size <= 10:
        objective, route = compute_exact_baseline(duration_matrix)
        method = "exact_permutation"
    else:
        objective, route = compute_best_known_baseline(duration_matrix, time_limit_seconds)
        method = "extended_ortools"

    baselines[key] = {
        "size": size,
        "objective": objective,
        "route": route,
        "method": method,
        "time_limit_seconds": time_limit_seconds if size > 10 else None,
    }
    return baselines[key]


def compute_exact_baseline(duration_matrix: list[list[int]]) -> tuple[int, list[int]]:
    best_objective: int | None = None
    best_route: list[int] | None = None
    nodes = list(range(1, len(duration_matrix)))

    for permutation in itertools.permutations(nodes):
        route = [0, *permutation, 0]
        objective = route_objective(duration_matrix, route)
        if best_objective is None or objective < best_objective:
            best_objective = objective
            best_route = list(route)

    if best_objective is None or best_route is None:
        raise RuntimeError("failed to compute exact baseline")

    return best_objective, best_route


def compute_best_known_baseline(
    duration_matrix: list[list[int]],
    time_limit_seconds: int,
) -> tuple[int, list[int]]:
    manager = pywrapcp.RoutingIndexManager(len(duration_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def callback(from_index: int, to_index: int) -> int:
        return duration_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = time_limit_seconds
    search_parameters.log_search = False

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        raise RuntimeError("baseline OR-Tools run returned no solution")

    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    route.append(manager.IndexToNode(index))
    return route_objective(duration_matrix, route), route


def route_objective(duration_matrix: list[list[int]], visit_order: list[int]) -> int:
    objective = 0
    for origin, destination in zip(visit_order, visit_order[1:]):
        objective += int(duration_matrix[origin][destination])
    return objective
