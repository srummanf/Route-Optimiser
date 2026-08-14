import solver


def test_solve_route_starts_and_ends_at_depot_and_visits_each_stop_once():
    duration_matrix = [
        [0, 10, 20, 30],
        [10, 0, 10, 20],
        [20, 10, 0, 10],
        [30, 20, 10, 0],
    ]

    route = solver.solve_route(duration_matrix)

    assert route[0] == 0
    assert route[-1] == 0
    assert sorted(route[1:-1]) == [1, 2, 3]
    assert len(route[1:-1]) == len(set(route[1:-1]))


def test_solve_route_returns_none_when_ortools_finds_no_solution(monkeypatch):
    class NoSolutionRoutingModel:
        def __init__(self, manager):
            self.manager = manager

        def RegisterTransitCallback(self, callback):
            return 0

        def SetArcCostEvaluatorOfAllVehicles(self, callback_index):
            pass

        def SolveWithParameters(self, search_parameters):
            return None

    monkeypatch.setattr(solver.pywrapcp, "RoutingModel", NoSolutionRoutingModel)

    assert solver.solve_route([[0, 1], [1, 0]]) is None
