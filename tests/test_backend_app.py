import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import app as route_app


def stops(count):
    return [
        {
            "lat": 22.0 + index,
            "lng": 88.0 + index
        }
        for index in range(count)
    ]


def matrix(size):
    return [
        [
            0 if row == col else 60
            for col in range(size)
        ]
        for row in range(size)
    ]


class RouteLimitTests(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(route_app.app)

    def optimize_with_mocks(self, stop_count):
        visit_order = list(range(stop_count)) + [0]

        with patch.object(
            route_app,
            "build_duration_matrix",
            Mock(return_value=(matrix(stop_count), matrix(stop_count)))
        ) as build_duration_matrix, patch.object(
            route_app,
            "solve_route",
            Mock(return_value=visit_order)
        ) as solve_route, patch.object(
            route_app,
            "get_route_geometry",
            Mock(
                return_value={
                    "distance": 1200,
                    "duration": 600,
                    "geometry": []
                }
            )
        ) as get_route_geometry:

            response = self.client.post(
                "/optimize",
                json={
                    "stops": stops(stop_count)
                }
            )

        return (
            response,
            build_duration_matrix,
            solve_route,
            get_route_geometry
        )

    def test_two_stops_remain_eligible_for_optimization(self):
        response, build_matrix, solve_route, route_geometry = (
            self.optimize_with_mocks(2)
        )

        self.assertEqual(response.status_code, 200)
        build_matrix.assert_called_once()
        solve_route.assert_called_once()
        route_geometry.assert_called_once()

    def test_twenty_five_stops_pass_validation(self):
        response, build_matrix, solve_route, route_geometry = (
            self.optimize_with_mocks(route_app.MAX_STOPS)
        )

        self.assertEqual(response.status_code, 200)
        build_matrix.assert_called_once()
        solve_route.assert_called_once()
        route_geometry.assert_called_once()

    def test_twenty_six_stops_return_422_before_downstream_calls(self):
        with patch.object(
            route_app,
            "build_duration_matrix"
        ) as build_matrix, patch.object(
            route_app,
            "solve_route"
        ) as solve_route, patch.object(
            route_app,
            "get_route_geometry"
        ) as route_geometry:

            response = self.client.post(
                "/optimize",
                json={
                    "stops": stops(route_app.MAX_STOPS + 1)
                }
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())
        build_matrix.assert_not_called()
        solve_route.assert_not_called()
        route_geometry.assert_not_called()

    def test_config_exposes_authoritative_limit(self):
        response = self.client.get("/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "max_stops": route_app.MAX_STOPS
            }
        )


if __name__ == "__main__":
    unittest.main()
