/* Driver dashboard controller for map rendering and booking actions. */
(function () {
    const config = window.driverDashboardConfig;
    const driverDataNode = document.getElementById("driver-data");
    const bookingDataNode = document.getElementById("driver-booking-data");
    if (!config || !driverDataNode || !window.L) {
        return;
    }

    const driver = JSON.parse(driverDataNode.textContent);
    const booking = bookingDataNode.textContent ? JSON.parse(bookingDataNode.textContent) : null;
    const mapElement = document.getElementById("driver-map");
    const offlineState = document.getElementById("offline-state");
    const toggle = document.getElementById("availability-toggle");
    const statusPill = document.getElementById("driver-status-pill");
    const actionMessage = document.getElementById("driver-action-message");
    const actionButtons = document.querySelectorAll("[data-driver-action]");
    let map;
    let routeLayer;
    let watchId;
    let driverMarker;

    function setMessage(text, tone) {
        actionMessage.textContent = text || "";
        actionMessage.className = "form-message";
        if (tone) {
            actionMessage.classList.add(tone);
        }
    }

    function updateStatusPill(state) {
        statusPill.textContent = state;
        statusPill.className = "status-pill";
        if (state === "On") {
            statusPill.classList.add("online");
        } else if (state === "Busy") {
            statusPill.classList.add("busy");
        } else {
            statusPill.classList.add("offline");
        }
    }

    function postAction(url, payload) {
        const body = new URLSearchParams(payload || {});
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": config.csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
            body,
        }).then((response) => response.json());
    }

    function showOfflineState(isOffline) {
        offlineState.style.display = isOffline ? "flex" : "none";
        mapElement.style.visibility = isOffline ? "hidden" : "visible";
    }

    function initMap() {
        const initialLat = Number(driver.lat) || 20.5937;
        const initialLng = Number(driver.lng) || 78.9629;
        map = L.map(mapElement).setView([initialLat, initialLng], driver.lat && driver.lng ? 13 : 5);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);

        if (driver.lat && driver.lng) {
            driverMarker = L.marker([driver.lat, driver.lng]).addTo(map).bindPopup("Driver location");
        }

        if (booking) {
            L.marker([booking.pickup_lat, booking.pickup_lng]).addTo(map).bindPopup(`Pickup: ${booking.phone}`);
            if (booking.hospital_lat && booking.hospital_lng) {
                L.marker([booking.hospital_lat, booking.hospital_lng]).addTo(map).bindPopup(booking.hospital_name);
            }
            drawRoute();
        }
    }

    async function drawRoute() {
        if (!driver.lat || !driver.lng || !booking || !booking.hospital_lat || !booking.hospital_lng) {
            return;
        }

        const url = `https://router.project-osrm.org/route/v1/driving/${driver.lng},${driver.lat};${booking.pickup_lng},${booking.pickup_lat};${booking.hospital_lng},${booking.hospital_lat}?overview=full&geometries=geojson`;
        const response = await fetch(url);
        const data = await response.json();
        const route = data.routes && data.routes[0];
        if (!route) {
            return;
        }

        if (routeLayer) {
            map.removeLayer(routeLayer);
        }

        routeLayer = L.geoJSON(route.geometry, {
            style: {
                color: "#e14942",
                weight: 5,
            },
        }).addTo(map);

        map.fitBounds(routeLayer.getBounds(), { padding: [30, 30] });
    }

    function startLocationWatch() {
        if (!navigator.geolocation || watchId || driver.state === "Off") {
            return;
        }

        watchId = navigator.geolocation.watchPosition(
            async (position) => {
                driver.lat = Number(position.coords.latitude.toFixed(5));
                driver.lng = Number(position.coords.longitude.toFixed(5));

                if (driverMarker) {
                    driverMarker.setLatLng([driver.lat, driver.lng]);
                } else {
                    driverMarker = L.marker([driver.lat, driver.lng]).addTo(map).bindPopup("Driver location");
                }

                await postAction(config.urls.updateLocation, {
                    lat: driver.lat,
                    lon: driver.lng,
                });

                if (booking) {
                    drawRoute();
                }
            },
            () => setMessage("Location permission is needed for live tracking.", "error"),
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
        );
    }

    function stopLocationWatch() {
        if (watchId) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
    }

    toggle.addEventListener("change", async () => {
        const state = toggle.checked ? "On" : "Off";
        const response = await postAction(config.urls.toggle, { state });

        if (response.status === "ok") {
            driver.state = response.state;
            updateStatusPill(driver.state);
            showOfflineState(driver.state === "Off");
            if (driver.state === "Off") {
                stopLocationWatch();
            } else {
                startLocationWatch();
            }
            setMessage(`Driver status updated to ${driver.state}.`, "success");
            return;
        }

        setMessage("Could not update availability.", "error");
    });

    actionButtons.forEach((button) => {
        button.addEventListener("click", async () => {
            const action = button.dataset.driverAction;
            const actionMap = {
                accept: config.urls.accept,
                reject: config.urls.reject,
                start: config.urls.start,
                complete: config.urls.complete,
            };

            setMessage("Updating booking...");
            const response = await postAction(actionMap[action], {});
            if (response.status) {
                setMessage(`Booking action "${action}" completed. Refreshing view...`, "success");
                window.setTimeout(() => window.location.reload(), 800);
            }
        });
    });

    initMap();
    showOfflineState(driver.state === "Off");
    updateStatusPill(driver.state);
    if (driver.state !== "Off") {
        startLocationWatch();
    }
})();
