from unittest.mock import Mock

from fastapi.testclient import TestClient

import app as app_module


client = TestClient(app_module.app)


def test_optimize_rejects_too_few_stops_without_calling_osrm(monkeypatch):
    build_duration_matrix = Mock()
    get_route_geometry = Mock()
    monkeypatch.setattr(app_module, "build_duration_matrix", build_duration_matrix)
    monkeypatch.setattr(app_module, "get_route_geometry", get_route_geometry)

    response = client.post("/optimize", json={"stops": [{"lat": 1, "lng": 2}]})

    assert response.status_code == 200
    assert response.json() == {"error": "Need at least 2 stops"}
    build_duration_matrix.assert_not_called()
    get_route_geometry.assert_not_called()


def test_optimize_returns_route_data_from_mocked_osrm(monkeypatch):
    locations = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
    build_duration_matrix = Mock(return_value=(
        [[0, 10, 20], [10, 0, 10], [20, 10, 0]],
        [[0, 100, 200], [100, 0, 100], [200, 100, 0]],
    ))
    get_route_geometry = Mock(return_value={
        "distance": 1234.56,
        "duration": 367.0,
        "geometry": [[2.0, 1.0], [6.0, 5.0], [4.0, 3.0], [2.0, 1.0]],
    })
    monkeypatch.setattr(app_module, "build_duration_matrix", build_duration_matrix)
    monkeypatch.setattr(app_module, "get_route_geometry", get_route_geometry)
    monkeypatch.setattr(app_module, "solve_route", Mock(return_value=[0, 2, 1, 0]))

    response = client.post("/optimize", json={
        "stops": [{"lat": lat, "lng": lng} for lat, lng in locations],
    })

    assert response.status_code == 200
    assert response.json() == {
        "visit_order": [0, 2, 1, 0],
        "total_distance_m": 1235,
        "total_duration_min": 6.1,
        "geometry": [[2.0, 1.0], [6.0, 5.0], [4.0, 3.0], [2.0, 1.0]],
    }
    build_duration_matrix.assert_called_once_with(locations)
    get_route_geometry.assert_called_once_with(locations, [0, 2, 1, 0])


def test_optimize_maps_no_solution_to_existing_error(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "build_duration_matrix",
        Mock(return_value=([[0, 1], [1, 0]], [[0, 1], [1, 0]])),
    )
    monkeypatch.setattr(app_module, "solve_route", Mock(return_value=None))
    get_route_geometry = Mock()
    monkeypatch.setattr(app_module, "get_route_geometry", get_route_geometry)

    response = client.post("/optimize", json={
        "stops": [{"lat": 1, "lng": 2}, {"lat": 3, "lng": 4}],
    })

    assert response.status_code == 200
    assert response.json() == {"error": "No solution found"}
    get_route_geometry.assert_not_called()
