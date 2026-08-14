import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))

import app as app_module  # noqa: E402
import osrm_service  # noqa: E402


client = TestClient(app_module.app)

VALID_STOPS = {
    "stops": [
        {"lat": 22.5726, "lng": 88.3639},
        {"lat": 22.58, "lng": 88.37},
    ]
}

VALID_TABLE = {
    "code": "Ok",
    "durations": [
        [0, 300],
        [320, 0],
    ],
    "distances": [
        [0, 1200],
        [1250, 0],
    ],
}

VALID_ROUTE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 1250,
            "duration": 320,
            "geometry": {
                "coordinates": [
                    [88.3639, 22.5726],
                    [88.37, 22.58],
                ]
            },
        }
    ],
}

ROUTING_ERROR = {
    "detail": {
        "error": {
            "code": "routing_upstream_error",
            "message": (
                "Routing provider returned an invalid or unavailable response. "
                "Please retry the request."
            ),
        }
    }
}


class FakeResponse:
    def __init__(self, payload=None, status_error=None, json_error=None):
        self.payload = payload
        self.status_error = status_error
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


def mock_osrm_responses(monkeypatch, *responses):
    request_mock = Mock(side_effect=responses)
    monkeypatch.setattr(osrm_service.requests, "get", request_mock)
    return request_mock


def assert_routing_error(response):
    assert response.status_code == 502
    assert response.json() == ROUTING_ERROR


@pytest.mark.parametrize(
    "osrm_result",
    [
        FakeResponse(
            status_error=requests.HTTPError("bad gateway")
        ),
        requests.Timeout("timed out"),
        FakeResponse(json_error=ValueError("invalid json")),
        FakeResponse({"code": "NoTable"}),
    ],
)
def test_optimize_returns_502_for_table_upstream_failures(
    monkeypatch,
    osrm_result,
):
    mock_osrm_responses(monkeypatch, osrm_result)
    solve_mock = Mock()
    monkeypatch.setattr(app_module, "solve_route", solve_mock)

    response = client.post("/optimize", json=VALID_STOPS)

    assert_routing_error(response)
    solve_mock.assert_not_called()


@pytest.mark.parametrize(
    "table_payload",
    [
        {
            "code": "Ok",
            "durations": [[0, 300]],
            "distances": [[0, 1200], [1250, 0]],
        },
        {
            "code": "Ok",
            "durations": [[0, None], [320, 0]],
            "distances": [[0, 1200], [1250, 0]],
        },
        {
            "code": "Ok",
            "durations": [[0, "300"], [320, 0]],
            "distances": [[0, 1200], [1250, 0]],
        },
        {
            "code": "Ok",
            "durations": [[0, 300], [320, 0]],
            "distances": [[0], [1250]],
        },
    ],
)
def test_optimize_returns_502_for_invalid_matrices_without_solver(
    monkeypatch,
    table_payload,
):
    mock_osrm_responses(monkeypatch, FakeResponse(table_payload))
    solve_mock = Mock()
    monkeypatch.setattr(app_module, "solve_route", solve_mock)

    response = client.post("/optimize", json=VALID_STOPS)

    assert_routing_error(response)
    solve_mock.assert_not_called()


@pytest.mark.parametrize(
    "route_payload",
    [
        {"code": "NoRoute", "routes": []},
        {"code": "Ok", "routes": []},
        {
            "code": "Ok",
            "routes": [
                {
                    "distance": 1250,
                    "duration": 320,
                }
            ],
        },
        {
            "code": "Ok",
            "routes": [
                {
                    "distance": None,
                    "duration": 320,
                    "geometry": {"coordinates": []},
                }
            ],
        },
    ],
)
def test_optimize_returns_502_for_invalid_route_responses(
    monkeypatch,
    route_payload,
):
    mock_osrm_responses(
        monkeypatch,
        FakeResponse(VALID_TABLE),
        FakeResponse(route_payload),
    )
    solve_mock = Mock(return_value=[0, 1, 0])
    monkeypatch.setattr(app_module, "solve_route", solve_mock)

    response = client.post("/optimize", json=VALID_STOPS)

    assert_routing_error(response)
    solve_mock.assert_called_once_with(VALID_TABLE["durations"])


def test_optimize_valid_osrm_data_still_succeeds(monkeypatch):
    mock_osrm_responses(
        monkeypatch,
        FakeResponse(VALID_TABLE),
        FakeResponse(VALID_ROUTE),
    )
    monkeypatch.setattr(
        app_module,
        "solve_route",
        Mock(return_value=[0, 1, 0]),
    )

    response = client.post("/optimize", json=VALID_STOPS)

    assert response.status_code == 200
    assert response.json() == {
        "visit_order": [0, 1, 0],
        "total_distance_m": 1250,
        "total_duration_min": 5.3,
        "geometry": [
            [88.3639, 22.5726],
            [88.37, 22.58],
        ],
    }


def test_optimize_rejects_fewer_than_two_stops(monkeypatch):
    solve_mock = Mock()
    monkeypatch.setattr(app_module, "solve_route", solve_mock)

    response = client.post(
        "/optimize",
        json={"stops": [{"lat": 22.5726, "lng": 88.3639}]},
    )

    assert response.status_code == 422
    solve_mock.assert_not_called()


def test_optimize_preserves_malformed_request_422(monkeypatch):
    solve_mock = Mock()
    monkeypatch.setattr(app_module, "solve_route", solve_mock)

    response = client.post(
        "/optimize",
        json={"stops": [{"lat": "not-a-lat", "lng": 88.3639}]},
    )

    assert response.status_code == 422
    solve_mock.assert_not_called()
