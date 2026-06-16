from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from osrm_service import (
    build_duration_matrix,
    get_route_geometry
)

from solver import solve_route

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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