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
let optimizeInFlight = false;
let routeGeneration = 0;

const optimizeBtn = document.getElementById("optimizeBtn");
const stats = document.getElementById("stats");
const defaultOptimizeLabel = optimizeBtn.textContent.trim();

function setOptimizeLoading(isLoading) {

    optimizeBtn.disabled = isLoading;
    optimizeBtn.textContent = isLoading
        ? "Optimizing..."
        : defaultOptimizeLabel;
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

    routeGeneration += 1;

    markers.forEach(
        m => map.removeLayer(m)
    );

    markers = [];

    if(routeLine) {
        map.removeLayer(routeLine);
        routeLine = null;
    }

    stats.innerHTML = "Add stops on map";
});

optimizeBtn
.addEventListener(
    "click",
    optimizeRoute
);

async function optimizeRoute() {

    if(optimizeInFlight) {
        return;
    }

    if(markers.length < 2) {

        alert(
            "Need at least 2 stops"
        );

        return;
    }

    optimizeInFlight = true;
    setOptimizeLoading(true);
    stats.innerHTML = "Optimizing route...";

    const requestGeneration = routeGeneration;

    const stops = markers.map(m => {

        const p = m.getLatLng();

        return {
            lat: p.lat,
            lng: p.lng
        };
    });

    try {

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

        if(requestGeneration !== routeGeneration) {
            return;
        }

        if(result.error) {

            alert(result.error);

            stats.innerHTML = result.error;

            return;
        }

        drawRoute(result.geometry);

        stats.innerHTML = `
            Stops: ${markers.length}<br>
            Distance:
            ${(result.total_distance_m/1000).toFixed(2)}
            km<br>
            Duration:
            ${result.total_duration_min}
            min
        `;
    }
    catch(error) {

        if(requestGeneration === routeGeneration) {

            alert("Optimization failed");

            stats.innerHTML = "Optimization failed";
        }
    }
    finally {

        optimizeInFlight = false;
        setOptimizeLoading(false);
    }
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
