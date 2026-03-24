(function () {
    const config = window.userTrackingConfig;
    if (!config || !window.L) return;

    const pickupLat     = JSON.parse(document.getElementById("tracking-pickup-lat").textContent);
    const pickupLng     = JSON.parse(document.getElementById("tracking-pickup-lng").textContent);
    const hospitalLat   = JSON.parse(document.getElementById("tracking-hospital-lat").textContent);
    const hospitalLng   = JSON.parse(document.getElementById("tracking-hospital-lng").textContent);
    const driverLatInit = JSON.parse(document.getElementById("tracking-driver-lat").textContent);
    const driverLngInit = JSON.parse(document.getElementById("tracking-driver-lng").textContent);
    const bookingId     = JSON.parse(document.getElementById("tracking-booking-id").textContent);
    const noteNode      = document.getElementById("tracking-note");

    // ── map setup — exposed globally so WS handler can move driverMarker ──
    const map = L.map("user-tracking-map").setView(
        [pickupLat || 20.5937, pickupLng || 78.9629],
        pickupLat ? 14 : 5
    );
    window.trackingMap = map;   // ← expose for WebSocket handler

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    // ── markers ──
    let routeLayer;

    if (pickupLat && pickupLng)
        L.marker([pickupLat, pickupLng]).addTo(map).bindPopup("Your pickup");

    if (hospitalLat && hospitalLng)
        L.marker([hospitalLat, hospitalLng]).addTo(map).bindPopup("Hospital");

    // Driver marker — exposed globally so WS can move it
    if (driverLatInit && driverLngInit) {
        window.driverMarker = L.marker([driverLatInit, driverLngInit])
            .addTo(map).bindPopup("Driver");
    } else {
        // Create off-screen marker so WS handler can move it when location arrives
        window.driverMarker = L.marker([pickupLat || 20.5937, pickupLng || 78.9629])
            .addTo(map).bindPopup("Driver");
    }

    // ── route ──
    function renderRoute(dLat, dLng) {
        if (!dLat || !dLng || !pickupLat || !hospitalLat) return;
        fetch(`https://router.project-osrm.org/route/v1/driving/${dLng},${dLat};${pickupLng},${pickupLat};${hospitalLng},${hospitalLat}?overview=full&geometries=geojson`)
            .then(r => r.json())
            .then(data => {
                const route = data.routes?.[0];
                if (!route) return;
                if (routeLayer) map.removeLayer(routeLayer);
                routeLayer = L.geoJSON(route.geometry, {
                    style: { color: "#e14942", weight: 5 }
                }).addTo(map);
                map.fitBounds(routeLayer.getBounds(), { padding: [30, 30] });
            });
    }

    renderRoute(driverLatInit, driverLngInit);

    // ── re-render route when WS moves driver marker ──
    // patch driverMarker.setLatLng to also redraw route
    const _origSetLatLng = window.driverMarker.setLatLng.bind(window.driverMarker);
    window.driverMarker.setLatLng = function(latlng) {
        _origSetLatLng(latlng);
        renderRoute(latlng[0], latlng[1]);
        return window.driverMarker;
    };

    // ── user live location ping ──
    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(
            (pos) => {
                const lat = Number(pos.coords.latitude.toFixed(5));
                const lng = Number(pos.coords.longitude.toFixed(5));
                // Draw/move user marker on map
                if (window.userPickupMarker) {
                    window.userPickupMarker.setLatLng([lat, lng]);
                } else {
                    window.userPickupMarker = L.marker([lat, lng], {
                        icon: L.icon({
                            iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                        })
                    }).addTo(map).bindPopup("Your location");
                }

                fetch(config.updateLocationUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-CSRFToken": config.csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new URLSearchParams({ lat, lon: lng }),
                });
                if (noteNode) noteNode.textContent = "Live location shared with dispatch.";
            },
            () => { if (noteNode) noteNode.textContent = "Location permission denied."; },
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
        );
    }
})();