from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2


def solve_route(duration_matrix):

    node_count = len(duration_matrix)

    manager = pywrapcp.RoutingIndexManager(
        node_count,
        1,
        0
    )

    routing = pywrapcp.RoutingModel(manager)

    def callback(from_index, to_index):

        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        return int(
            duration_matrix[from_node][to_node]
        )

    transit_index = routing.RegisterTransitCallback(
        callback
    )

    routing.SetArcCostEvaluatorOfAllVehicles(
        transit_index
    )

    search_parameters = (
        pywrapcp.DefaultRoutingSearchParameters()
    )

    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy
        .PATH_CHEAPEST_ARC
    )

    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic
        .GUIDED_LOCAL_SEARCH
    )

    search_parameters.time_limit.seconds = 5

    solution = routing.SolveWithParameters(
        search_parameters
    )

    if not solution:
        return None

    route = []

    index = routing.Start(0)

    while not routing.IsEnd(index):

        route.append(
            manager.IndexToNode(index)
        )

        index = solution.Value(
            routing.NextVar(index)
        )

    route.append(
        manager.IndexToNode(index)
    )

    return route