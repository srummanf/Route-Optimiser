# Route Optimizer

A delivery route optimization application built with:

- Python
- FastAPI
- Google OR-Tools
- OpenStreetMap (OSRM)
- Leaflet.js

The application calculates the fastest route for a driver to visit multiple delivery stops using real driving times instead of straight-line distances.

---

## Features

- Interactive map using Leaflet.js
- Click-to-add delivery stops
- Draggable markers
- Real driving-time matrix from OSRM
- Route optimization using Google OR-Tools
- Real road geometry visualization
- Distance and duration statistics
- FastAPI backend

---

## Architecture

```text
User
 │
 ▼
Leaflet Frontend
 │
 ▼
FastAPI Backend
 │
 ├── OSRM Table API
 │      └── Travel Time Matrix
 │
 ├── Google OR-Tools
 │      └── Optimal Stop Order
 │
 └── OSRM Route API
        └── Road Geometry
 │
 ▼
Leaflet Route Visualization
```

---

## Project Structure

```text
route-optimizer/

requirements.txt
constraints-py311.txt

backend/
│
├── app.py
├── solver.py
├── osrm_service.py
frontend/
│
├── index.html
├── app.js
├── style.css

.gitignore
README.md
```

---

## Prerequisites

Install:

- 64-bit CPython 3.11 on Linux x86_64 (the tested and supported runtime/platform)
- Git

Verify installation:

```bash
python --version  # must report Python 3.11.x
git --version
```

---

## Clone Repository

```bash
git clone <repository-url>

cd route-optimizer
```

---

## Backend Setup

### Create Virtual Environment

Windows

```bash
python -m venv venv

venv\Scripts\activate
```

Linux / Mac

```bash
python -m venv venv

source venv/bin/activate
```

---

### Install Dependencies

From the repository root, install the direct requirements together with the exact tested
transitive dependency set:

```bash
python -m pip install -r requirements.txt -c constraints-py311.txt
```

If you have already changed into `backend`, use the equivalent paths:

```bash
python -m pip install -r ../requirements.txt -c ../constraints-py311.txt
```

`requirements.txt` pins the five direct application dependencies. `constraints-py311.txt`
pins the complete resolution used for testing. Do not omit the constraints file when
recreating the supported environment.

### Updating and Reviewing Dependencies

Perform dependency updates manually so each change is tested and reviewed:

1. Create or activate a clean Python 3.11 virtual environment.
2. Update the requested direct version in `requirements.txt`, install the temporary
   tooling with `python -m pip install pip-tools`, and regenerate the lock input with
   `pip-compile --output-file constraints-py311.txt requirements.txt` using the same
   Python/platform target. Keep all direct and transitive versions exact.
3. Install from the canonical command above and run the application smoke check: start
   Uvicorn, open `/docs`, and submit a representative two-stop `/optimize` request.
4. Run `python -m pip check` and review the dependency tree with
   `python -m pip list --outdated`.
5. Install `pip-audit` in the temporary environment if it is not already available, then
   run `pip-audit -r constraints-py311.txt`. Resolve or document each reported
   vulnerability before merging.
6. Commit the updated requirements and constraints together, including the tested Python
   and platform details in the change description.

---

### Start FastAPI Server

```bash
uvicorn app:app --reload
```

Server runs at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

## Frontend Setup

Open a second terminal.

Navigate to frontend:

```bash
cd frontend
```

Start a simple HTTP server:

```bash
python -m http.server 5500
```

Frontend runs at:

```text
http://localhost:5500
```

---

## Usage

### Add Stops

- Open the application in a browser.
- Click anywhere on the map.
- Each click creates a delivery stop.
- Markers can be dragged to adjust locations.

### Optimize Route

Click:

```text
Optimize Route
```

The application will:

1. Collect all stop coordinates
2. Request a travel-time matrix from OSRM
3. Solve the route using OR-Tools
4. Request road geometry from OSRM
5. Draw the optimized route on the map

### Clear Route

Click:

```text
Clear
```

to remove all markers and route lines.

---

## How It Works

### Step 1: User Places Stops

Example:

```text
Depot
Stop A
Stop B
Stop C
```

---

### Step 2: OSRM Builds Travel Matrix

Example:

```text
          Depot   A    B    C

Depot       0    300  500  700
A          320    0   200  450
B          510   210   0   150
C          680   470  160   0
```

Values are travel times in seconds.

---

### Step 3: OR-Tools Solves Route

Possible route:

```text
Depot → A → B → C
```

Possible route:

```text
Depot → C → B → A
```

OR-Tools evaluates many combinations and chooses the lowest-cost route.

---

### Step 4: OSRM Generates Actual Road Geometry

Instead of drawing straight lines:

```text
A ---------- B
```

OSRM returns actual road paths:

```text
A → Street → Highway → Road → B
```

---

### Step 5: Leaflet Displays Route

The optimized route is drawn on the map and route statistics are displayed.

---

## API Example

### Request

```http
POST /optimize
```

```json
{
  "stops": [
    {
      "lat": 22.5726,
      "lng": 88.3639
    },
    {
      "lat": 22.5800,
      "lng": 88.3700
    },
    {
      "lat": 22.5900,
      "lng": 88.3400
    }
  ]
}
```

---

### Response

```json
{
  "visit_order": [0, 2, 1],
  "total_distance_m": 12750,
  "total_duration_min": 28.4,
  "geometry": [...]
}
```

---

## Technology Stack

### Backend

- FastAPI
- OR-Tools
- Requests
- Pydantic

### Routing Engine

- OSRM
- OpenStreetMap

### Frontend

- Leaflet.js
- OpenStreetMap Tiles
- Vanilla JavaScript

---

## Future Enhancements

### Routing

- Multiple vehicles
- Multiple depots
- Driver shifts
- Delivery time windows
- Capacity constraints
- Route balancing

### Mapping

- Stop numbering
- Route coloring
- Live GPS tracking
- Traffic-aware routing

### Infrastructure

- Docker
- Self-hosted OSRM
- PostgreSQL
- PostGIS
- Redis caching

### Operations

- Route export
- CSV import
- Batch optimization
- Historical route storage

---

## Development Notes

The public OSRM server is intended for development and testing.

For production workloads:

- Deploy a self-hosted OSRM instance
- Cache route matrices
- Add rate limiting
- Store routes in a database

---

## License

This project is provided for educational and portfolio purposes.
