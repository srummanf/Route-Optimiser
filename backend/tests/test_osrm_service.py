import unittest

from backend.osrm_service import (
    DEFAULT_OSRM_BASE_URL,
    DEFAULT_OSRM_TIMEOUT_SECONDS,
    OSRMService,
    OsrmConfigurationError,
    OsrmConfig,
    load_osrm_config
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpGet:
    def __init__(self):
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if "/table/" in url:
            return FakeResponse({
                "durations": [[0, 10], [12, 0]],
                "distances": [[0, 100], [120, 0]]
            })

        return FakeResponse({
            "routes": [{
                "distance": 1234.5,
                "duration": 678.9,
                "geometry": {
                    "coordinates": [
                        [88.3639, 22.5726],
                        [88.3700, 22.5800]
                    ]
                }
            }]
        })


class OSRMServiceTest(unittest.TestCase):
    def test_table_call_uses_configured_host_and_timeout(self):
        fake_get = FakeHttpGet()
        service = OSRMService(
            config=OsrmConfig(
                base_url="http://osrm.local:5000",
                timeout_seconds=4.5
            ),
            http_get=fake_get
        )

        durations, distances = service.build_duration_matrix([
            (22.5726, 88.3639),
            (22.5800, 88.3700)
        ])

        self.assertEqual(durations, [[0, 10], [12, 0]])
        self.assertEqual(distances, [[0, 100], [120, 0]])
        self.assertEqual(len(fake_get.calls), 1)
        url, kwargs = fake_get.calls[0]
        self.assertEqual(
            url,
            "http://osrm.local:5000/table/v1/driving/"
            "88.3639,22.5726;88.37,22.58"
            "?annotations=duration,distance"
        )
        self.assertEqual(kwargs["timeout"], 4.5)

    def test_route_call_uses_configured_host_and_timeout(self):
        fake_get = FakeHttpGet()
        service = OSRMService(
            config=OsrmConfig(
                base_url="https://routes.example",
                timeout_seconds=2.0
            ),
            http_get=fake_get
        )

        route = service.get_route_geometry(
            [
                (22.5726, 88.3639),
                (22.5800, 88.3700)
            ],
            [1, 0]
        )

        self.assertEqual(route["distance"], 1234.5)
        self.assertEqual(route["duration"], 678.9)
        self.assertEqual(
            route["geometry"],
            [[88.3639, 22.5726], [88.3700, 22.5800]]
        )
        self.assertEqual(len(fake_get.calls), 1)
        url, kwargs = fake_get.calls[0]
        self.assertEqual(
            url,
            "https://routes.example/route/v1/driving/"
            "88.37,22.58;88.3639,22.5726"
            "?overview=full"
            "&geometries=geojson"
            "&steps=false"
        )
        self.assertEqual(kwargs["timeout"], 2.0)

    def test_defaults_preserve_public_osrm_and_timeout(self):
        config = load_osrm_config({})

        self.assertEqual(config.base_url, DEFAULT_OSRM_BASE_URL)
        self.assertEqual(
            config.timeout_seconds,
            DEFAULT_OSRM_TIMEOUT_SECONDS
        )

    def test_invalid_base_url_fails_configuration(self):
        with self.assertRaisesRegex(
            OsrmConfigurationError,
            "OSRM_BASE_URL"
        ):
            load_osrm_config({
                "OSRM_BASE_URL": "localhost:5000"
            })

    def test_invalid_timeout_fails_configuration(self):
        for timeout in ("0", "-1", "inf", "not-a-number"):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(
                    OsrmConfigurationError,
                    "OSRM_TIMEOUT_SECONDS"
                ):
                    load_osrm_config({
                        "OSRM_TIMEOUT_SECONDS": timeout
                    })


if __name__ == "__main__":
    unittest.main()
