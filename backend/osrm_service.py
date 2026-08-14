from numbers import Real

import requests

OSRM_BASE_URL = "https://router.project-osrm.org"
ROUTING_ERROR_CODE = "routing_upstream_error"
ROUTING_ERROR_MESSAGE = (
    "Routing provider returned an invalid or unavailable response. "
    "Please retry the request."
)


class RoutingServiceError(Exception):
    def __init__(self, message=ROUTING_ERROR_MESSAGE):
        super().__init__(message)
        self.code = ROUTING_ERROR_CODE
        self.message = message


def _request_json(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ) as exc:
        raise RoutingServiceError() from exc


def _is_number(value):
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
    )


def _validate_matrix(matrix, expected_size):
    if (
        not isinstance(matrix, list)
        or len(matrix) != expected_size
    ):
        raise RoutingServiceError()

    for row in matrix:
        if (
            not isinstance(row, list)
            or len(row) != expected_size
        ):
            raise RoutingServiceError()

        for value in row:
            if not _is_number(value):
                raise RoutingServiceError()

    return matrix


def build_duration_matrix(locations):
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
        f"{OSRM_BASE_URL}/table/v1/driving/"
        f"{coordinates}"
        "?annotations=duration,distance"
    )

    data = _request_json(url)

    if (
        not isinstance(data, dict)
        or data.get("code") != "Ok"
    ):
        raise RoutingServiceError()

    duration_matrix = _validate_matrix(
        data.get("durations"),
        len(locations),
    )
    distance_matrix = _validate_matrix(
        data.get("distances"),
        len(locations),
    )

    return duration_matrix, distance_matrix


def get_route_geometry(locations, visit_order):
    """
    Returns actual road geometry.
    """

    ordered = [locations[i] for i in visit_order]

    coordinates = ";".join(
        f"{lon},{lat}"
        for lat, lon in ordered
    )

    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{coordinates}"
        "?overview=full"
        "&geometries=geojson"
        "&steps=false"
    )

    data = _request_json(url)

    if (
        not isinstance(data, dict)
        or data.get("code") != "Ok"
        or not isinstance(data.get("routes"), list)
        or not data["routes"]
    ):
        raise RoutingServiceError()

    route = data["routes"][0]

    if (
        not isinstance(route, dict)
        or not _is_number(route.get("distance"))
        or not _is_number(route.get("duration"))
        or not isinstance(route.get("geometry"), dict)
        or not isinstance(
            route["geometry"].get("coordinates"),
            list
        )
    ):
        raise RoutingServiceError()

    return {
        "distance": route["distance"],
        "duration": route["duration"],
        "geometry": route["geometry"]["coordinates"]
    }
