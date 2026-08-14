const assert = require("node:assert/strict");
const test = require("node:test");

const {
    requestOptimizedRoute,
    showOptimizationError,
    showRouteStats
} = require("./app.js");

function okResponse(result) {

    return {
        ok: true,
        status: 200,
        json: async () => result
    };
}

function createStatsDocument(initialHtml = "") {

    const stats = {
        innerHTML: initialHtml,
        statusElement: null,
        prepend(element) {
            this.statusElement = element;
        },
        querySelector(selector) {

            if(selector === ".route-status") {
                return this.statusElement;
            }

            return null;
        }
    };

    global.document = {
        createElement: () => ({
            className: "",
            textContent: ""
        }),
        getElementById: id => {

            assert.equal(id, "stats");
            return stats;
        }
    };

    return stats;
}

test("requestOptimizedRoute posts stops and returns successful results", async () => {

    const stops = [
        {
            lat: 22.1,
            lng: 88.1
        },
        {
            lat: 22.2,
            lng: 88.2
        }
    ];
    const result = {
        geometry: [[88.1, 22.1]],
        total_distance_m: 1234,
        total_duration_min: 8
    };

    const response = await requestOptimizedRoute(
        stops,
        async (url, options) => {

            assert.equal(
                url,
                "http://localhost:8000/optimize"
            );
            assert.equal(options.method, "POST");
            assert.deepEqual(
                JSON.parse(options.body),
                {
                    stops
                }
            );

            return okResponse(result);
        }
    );

    assert.equal(response, result);
});

test("requestOptimizedRoute reports network rejection", async () => {

    await assert.rejects(
        requestOptimizedRoute(
            [],
            async () => {
                throw new Error("connection refused");
            }
        ),
        error => error.type === "network" &&
            error.message.includes("could not reach the server")
    );
});

test("requestOptimizedRoute reports non-2xx responses", async () => {

    await assert.rejects(
        requestOptimizedRoute(
            [],
            async () => ({
                ok: false,
                status: 503,
                json: async () => ({})
            })
        ),
        error => error.type === "http" &&
            error.message.includes("Status 503")
    );
});

test("requestOptimizedRoute reports invalid JSON", async () => {

    await assert.rejects(
        requestOptimizedRoute(
            [],
            async () => ({
                ok: true,
                status: 200,
                json: async () => {
                    throw new SyntaxError("Unexpected token");
                }
            })
        ),
        error => error.type === "json" &&
            error.message.includes("unreadable response")
    );
});

test("requestOptimizedRoute reports backend application errors", async () => {

    await assert.rejects(
        requestOptimizedRoute(
            [],
            async () => okResponse({
                error: "No feasible route"
            })
        ),
        error => error.type === "application" &&
            error.message.includes("No feasible route")
    );
});

test("showRouteStats renders successful route statistics", () => {

    const stats = createStatsDocument();

    showRouteStats(
        {
            total_distance_m: 2500,
            total_duration_min: 17
        },
        3
    );

    assert.match(stats.innerHTML, /Route optimized\./);
    assert.match(stats.innerHTML, /Stops: 3/);
    assert.match(stats.innerHTML, /2\.50/);
    assert.match(stats.innerHTML, /17/);
});

test("showOptimizationError preserves existing route statistics", () => {

    const stats = createStatsDocument(
        "<div class=\"route-metrics\">Stops: 2<br>Distance: 1.00 km</div>"
    );

    showOptimizationError(
        new Error("Route optimization failed. Use Optimize Route to retry.")
    );

    assert.equal(
        stats.statusElement.textContent,
        "Route optimization failed. Use Optimize Route to retry."
    );
    assert.equal(
        stats.statusElement.className,
        "route-status route-status--error"
    );
    assert.match(stats.innerHTML, /Distance: 1\.00 km/);
});
