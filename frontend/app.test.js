const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function createDocument() {
    const listeners = {};
    const elements = {
        stats: {
            innerHTML: "Add stops on map"
        },
        clearBtn: {
            addEventListener: (event, callback) => {
                listeners[`clearBtn:${event}`] = callback;
            }
        },
        optimizeBtn: {
            addEventListener: (event, callback) => {
                listeners[`optimizeBtn:${event}`] = callback;
            }
        }
    };

    return {
        listeners,
        getElementById: id => elements[id]
    };
}

function createLeafletMock() {
    const handlers = {};

    return {
        handlers,
        map: () => ({
            setView: () => ({
                on: (event, callback) => {
                    handlers[event] = callback;
                },
                removeLayer: () => {},
                fitBounds: () => {}
            })
        }),
        tileLayer: () => ({
            addTo: () => {}
        }),
        marker: latlng => ({
            addTo: () => ({
                bindTooltip: () => {},
                getLatLng: () => latlng
            })
        }),
        polyline: () => ({
            addTo: () => ({
                getBounds: () => ({})
            })
        })
    };
}

async function loadApp(fetchMock) {
    const document = createDocument();
    const leaflet = createLeafletMock();
    const source = fs.readFileSync(
        path.join(__dirname, "app.js"),
        "utf8"
    );

    const context = {
        alert: () => {},
        document,
        fetch: fetchMock,
        L: leaflet
    };

    vm.createContext(context);
    vm.runInContext(source, context);
    await Promise.resolve();
    await Promise.resolve();

    return {
        context,
        document,
        leaflet
    };
}

test("oversized marker sets use /config limit and do not post optimize", async () => {
    const calls = [];
    const fetchMock = async (url, options) => {
        calls.push({
            url,
            options
        });

        if(url.endsWith("/config")) {
            return {
                ok: true,
                json: async () => ({
                    max_stops: 25
                })
            };
        }

        throw new Error("Unexpected optimize request");
    };

    const { context, document, leaflet } = await loadApp(fetchMock);

    for(let index = 0; index < 26; index += 1) {
        leaflet.handlers.click({
            latlng: {
                lat: index,
                lng: index
            }
        });
    }

    await context.optimizeRoute();

    assert.deepEqual(
        calls.map(call => call.url),
        ["http://localhost:8000/config"]
    );
    assert.equal(
        document.getElementById("stats").innerHTML,
        "Routes can include at most 25 stops"
    );
});
