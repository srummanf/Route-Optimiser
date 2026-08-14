import math
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import requests

DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"
DEFAULT_OSRM_TIMEOUT_SECONDS = 30.0


class OsrmConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class OsrmConfig:
    base_url: str = DEFAULT_OSRM_BASE_URL
    timeout_seconds: float = DEFAULT_OSRM_TIMEOUT_SECONDS


HttpGet = Callable[..., Any]


def load_osrm_config(
    env: Mapping[str, str] | None = None
) -> OsrmConfig:
    env = os.environ if env is None else env
    base_url = env.get(
        "OSRM_BASE_URL",
        DEFAULT_OSRM_BASE_URL
    ).strip()
    timeout_value = env.get(
        "OSRM_TIMEOUT_SECONDS",
        str(DEFAULT_OSRM_TIMEOUT_SECONDS)
    ).strip()

    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
    ):
        raise OsrmConfigurationError(
            "OSRM_BASE_URL must be an absolute HTTP(S) URL; "
            f"got {base_url!r}"
        )

    try:
        timeout_seconds = float(timeout_value)
    except ValueError as exc:
        raise OsrmConfigurationError(
            "OSRM_TIMEOUT_SECONDS must be a positive finite number; "
            f"got {timeout_value!r}"
        ) from exc

    if (
        not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise OsrmConfigurationError(
            "OSRM_TIMEOUT_SECONDS must be a positive finite number; "
            f"got {timeout_value!r}"
        )

    return OsrmConfig(
        base_url=base_url.rstrip("/"),
        timeout_seconds=timeout_seconds
    )


class OSRMService:
    def __init__(
        self,
        config: OsrmConfig | None = None,
        http_get: HttpGet | None = None
    ):
        self.config = config or load_osrm_config()
        self.http_get = http_get or requests.get

    def build_duration_matrix(self, locations):
        """
        locations:
        [
            (lat, lon),
            ...
        ]
        """

        coordinates = ";".join(
            f"{lon},{lat}"
            for lat, lon in locations
        )

        url = (
            f"{self.config.base_url}/table/v1/driving/"
            f"{coordinates}"
            "?annotations=duration,distance"
        )

        response = self.http_get(
            url,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()

        data = response.json()

        return data["durations"], data["distances"]

    def get_route_geometry(self, locations, visit_order):
        """
        Returns actual road geometry.
        """

        ordered = [locations[i] for i in visit_order]

        coordinates = ";".join(
            f"{lon},{lat}"
            for lat, lon in ordered
        )

        url = (
            f"{self.config.base_url}/route/v1/driving/"
            f"{coordinates}"
            "?overview=full"
            "&geometries=geojson"
            "&steps=false"
        )

        response = self.http_get(
            url,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()

        data = response.json()

        route = data["routes"][0]

        return {
            "distance": route["distance"],
            "duration": route["duration"],
            "geometry": route["geometry"]["coordinates"]
        }


_default_service: OSRMService | None = None


def create_osrm_service(
    env: Mapping[str, str] | None = None,
    http_get: HttpGet | None = None
) -> OSRMService:
    return OSRMService(
        config=load_osrm_config(env),
        http_get=http_get
    )


def configure_default_osrm_service(service: OSRMService) -> None:
    global _default_service
    _default_service = service


def get_default_osrm_service() -> OSRMService:
    global _default_service
    if _default_service is None:
        _default_service = create_osrm_service()
    return _default_service


def build_duration_matrix(locations):
    """
    locations:
    [
        (lat, lon),
        ...
    ]
    """
    return get_default_osrm_service().build_duration_matrix(locations)


def get_route_geometry(locations, visit_order):
    """
    Returns actual road geometry.
    """
    return get_default_osrm_service().get_route_geometry(
        locations,
        visit_order
    )
