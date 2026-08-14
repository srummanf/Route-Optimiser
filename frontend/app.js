const map = L.map("map")
.setView([22.5726, 88.3639], 12);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19
    }
).addTo(map);

let markers = [];
let routeLine = null;
let maxStops = null;

const API_BASE_URL = "http://localhost:8000";

loadConfig();

async function loadConfig() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/config`
        );

        if(!response.ok) {
            throw new Error(
                "Unable to load route limits"
            );
        }

        const config = await response.json();

        maxStops = config.max_stops;
    } catch(error) {

        showError(
            "Unable to load route limits"
        );
    }
}

function showError(message) {

    document.getElementById(
        "stats"
    ).innerHTML = message;

    alert(message);
}

function refreshLabels() {

    markers.forEach((marker, idx) => {

        marker.bindTooltip(
            String(idx),
            {
                permanent: true,
                direction: "top"
            }
        );
    });
}

map.on("click", e => {

    const marker = L.marker(
        e.latlng,
        {
            draggable: true
        }
    ).addTo(map);

    markers.push(marker);

    refreshLabels();
});

document
.getElementById("clearBtn")
.addEventListener("click", () => {

    markers.forEach(
        m => map.removeLayer(m)
    );

    markers = [];

    if(routeLine) {
        map.removeLayer(routeLine);
    }

    document.getElementById(
        "stats"
    ).innerHTML = "Add stops on map";
});

document
.getElementById("optimizeBtn")
.addEventListener(
    "click",
    optimizeRoute
);

async function optimizeRoute() {

    if(markers.length < 2) {

        showError(
            "Need at least 2 stops"
        );

        return;
    }

    if(maxStops === null) {

        showError(
            "Route limits are still loading"
        );

        return;
    }

    if(markers.length > maxStops) {

        showError(
            `Routes can include at most ${maxStops} stops`
        );

        return;
    }

    const stops = markers.map(m => {

        const p = m.getLatLng();

        return {
            lat: p.lat,
            lng: p.lng
        };
    });

    const response = await fetch(
        `${API_BASE_URL}/optimize`,
        {
            method: "POST",
            headers: {
                "Content-Type":
                "application/json"
            },
            body: JSON.stringify({
                stops
            })
        }
    );

    const result = await response.json();

    if(result.error) {

        showError(result.error);

        return;
    }

    drawRoute(result.geometry);

    document.getElementById(
        "stats"
    ).innerHTML = `
        Stops: ${markers.length}<br>
        Distance:
        ${(result.total_distance_m/1000).toFixed(2)}
        km<br>
        Duration:
        ${result.total_duration_min}
        min
    `;
}

function drawRoute(geometry) {

    if(routeLine) {

        map.removeLayer(routeLine);
    }

    const points = geometry.map(
        coord => [
            coord[1],
            coord[0]
        ]
    );

    routeLine = L.polyline(
        points,
        {
            weight: 5
        }
    ).addTo(map);

    map.fitBounds(
        routeLine.getBounds(),
        {
            padding: [50,50]
        }
    );
}
