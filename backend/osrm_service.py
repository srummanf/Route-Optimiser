import requests

OSRM_BASE_URL = "https://router.project-osrm.org"


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

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    return data["durations"], data["distances"]


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

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    route = data["routes"][0]

    return {
        "distance": route["distance"],
        "duration": route["duration"],
        "geometry": route["geometry"]["coordinates"]
    }