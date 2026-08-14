const hasBrowserRuntime = (
    typeof window !== "undefined" &&
    typeof document !== "undefined" &&
    typeof L !== "undefined"
);

const map = hasBrowserRuntime
    ? L.map("map").setView([22.5726, 88.3639], 12)
    : null;

if(hasBrowserRuntime) {

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19
        }
    ).addTo(map);
}

let markers = [];
let routeLine = null;

const routeMessages = {
    network:
        "Route optimization could not reach the server. Check the connection and use Optimize Route to retry.",
    http:
        "Route optimization failed on the server. Use Optimize Route to retry.",
    json:
        "Route optimization returned an unreadable response. Use Optimize Route to retry.",
    application:
        "Route optimization could not be completed. Use Optimize Route to retry."
};

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

if(hasBrowserRuntime) {

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

        routeLine = null;

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
}

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

    showRouteStatus(
        "Optimizing route...",
        "pending"
    );

    let result;

    try {

        result = await requestOptimizedRoute(
            stops
        );
    } catch(error) {

        showOptimizationError(error);

        return;
    }

    drawRoute(result.geometry);

    showRouteStats(
        result,
        markers.length
    );
}

async function requestOptimizedRoute(
    stops,
    fetchImpl = fetch
) {

    let response;

    try {

        response = await fetchImpl(
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
    } catch(error) {

        throw createOptimizationError(
            "network",
            routeMessages.network
        );
    }

    if(!response.ok) {

        throw createOptimizationError(
            "http",
            `${routeMessages.http} Status ${response.status}.`
        );
    }

    let result;

    try {

        result = await response.json();
    } catch(error) {

        throw createOptimizationError(
            "json",
            routeMessages.json
        );
    }

    if(result.error) {

        throw createOptimizationError(
            "application",
            `${routeMessages.application} ${result.error}`
        );
    }

    return result;
}

function createOptimizationError(
    type,
    message
) {

    const error = new Error(message);
    error.type = type;
    return error;
}

function showOptimizationError(error) {

    showRouteStatus(
        error.message || routeMessages.application,
        "error"
    );
}

function showRouteStats(
    result,
    stopCount
) {

    const stats = getStatsElement();

    stats.innerHTML = `
        <div class="route-status route-status--success">
            Route optimized.
        </div>
        <div class="route-metrics">
        Stops: ${stopCount}<br>
        Distance:
        ${(result.total_distance_m/1000).toFixed(2)}
        km<br>
        Duration:
        ${result.total_duration_min}
        min
        </div>
    `;
}

function showRouteStatus(
    message,
    status
) {

    const stats = getStatsElement();
    let statusElement = stats.querySelector(
        ".route-status"
    );

    if(!statusElement) {

        statusElement = document.createElement(
            "div"
        );

        stats.prepend(statusElement);
    }

    statusElement.className =
        `route-status route-status--${status}`;
    statusElement.textContent = message;
}

function getStatsElement() {

    return document.getElementById(
        "stats"
    );
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

if(typeof module !== "undefined") {

    module.exports = {
        createOptimizationError,
        requestOptimizedRoute,
        routeMessages,
        showOptimizationError,
        showRouteStats,
        showRouteStatus
    };
}
