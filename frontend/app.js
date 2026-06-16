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

        alert(
            "Need at least 2 stops"
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
        "http://localhost:8000/optimize",
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

        alert(result.error);

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