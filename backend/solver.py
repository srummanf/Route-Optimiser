from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2


def solve_route(duration_matrix):
    """
    Solve a single-vehicle TSP using OR-Tools.

    Node 0 = depot/start/end
    """

    num_locations = len(duration_matrix)

    manager = pywrapcp.RoutingIndexManager(
        num_locations,
        1,      # vehicles
        0       # depot
    )

    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        return int(
            duration_matrix[from_node][to_node]
        )

    transit_callback_index = (
        routing.RegisterTransitCallback(
            time_callback
        )
    )

    routing.SetArcCostEvaluatorOfAllVehicles(
        transit_callback_index
    )

    search_parameters = (
        pywrapcp.DefaultRoutingSearchParameters()
    )

    #
    # Better initial solution
    #
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy
        .PARALLEL_CHEAPEST_INSERTION
    )

    #
    # Strong local optimization
    #
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic
        .GUIDED_LOCAL_SEARCH
    )

    #
    # Give OR-Tools more time
    #
    search_parameters.time_limit.seconds = 30

    #
    # Continue improving even after first solution
    #
    search_parameters.log_search = True

    solution = routing.SolveWithParameters(
        search_parameters
    )

    if solution is None:
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