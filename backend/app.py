import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from osrm_service import (
    build_duration_matrix,
    get_route_geometry
)

from solver import solve_route

DEFAULT_ALLOWED_ORIGIN = "http://localhost:5500"


def get_allowed_origins(value: str | None = None) -> list[str]:
    """Return configured origins and refuse wildcard credentialed CORS."""
    configured = os.getenv("CORS_ALLOWED_ORIGINS") if value is None else value
    origins = [origin.strip() for origin in (configured or DEFAULT_ALLOWED_ORIGIN).split(",")]
    origins = [origin for origin in origins if origin]

    if not origins or "*" in origins:
        raise ValueError(
            "CORS_ALLOWED_ORIGINS cannot contain '*' when credentials are enabled"
        )

    return origins


def create_app(allowed_origins: str | None = None) -> FastAPI:
    application = FastAPI()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return application


app = create_app()


class Stop(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    stops: list[Stop]


@app.post("/optimize")
def optimize_route(request: RouteRequest):

    if len(request.stops) < 2:
        return {
            "error": "Need at least 2 stops"
        }

    locations = [
        (s.lat, s.lng)
        for s in request.stops
    ]

    duration_matrix, distance_matrix = (
        build_duration_matrix(locations)
    )

    visit_order = solve_route(duration_matrix)

    if not visit_order:
        return {
            "error": "No solution found"
        }

    route_data = get_route_geometry(
        locations,
        visit_order
    )

    return {
        "visit_order": visit_order,
        "total_distance_m": round(
            route_data["distance"]
        ),
        "total_duration_min": round(
            route_data["duration"] / 60,
            1
        ),
        "geometry": route_data["geometry"]
    }
