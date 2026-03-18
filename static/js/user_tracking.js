/* Rider pickup tracking controller with live user-location pinging. */
(function () {
    const config = window.userTrackingConfig;
    if (!config || !window.L) {
        return;
    }

    const bookingId = JSON.parse(document.getElementById("tracking-booking-id").textContent);
    const pickupLat = JSON.parse(document.getElementById("tracking-pickup-lat").textContent);
    const pickupLng = JSON.parse(document.getElementById("tracking-pickup-lng").textContent);
    const hospitalLat = JSON.parse(document.getElementById("tracking-hospital-lat").textContent);
    const hospitalLng = JSON.parse(document.getElementById("tracking-hospital-lng").textContent);
    const initialDriverLat = JSON.parse(document.getElementById("tracking-driver-lat").textContent);
    const initialDriverLng = JSON.parse(document.getElementById("tracking-driver-lng").textContent);
    const statusNode = document.getElementById("tracking-status");
    const driverNode = document.getElementById("tracking-driver");
    const hospitalNode = document.getElementById("tracking-hospital");
    const noteNode = document.getElementById("tracking-note");

    const map = L.map("user-tracking-map").setView([pickupLat || 20.5937, pickupLng || 78.9629], pickupLat && pickupLng ? 14 : 5);
    let driverMarker;
    let userMarker;
    let hospitalMarker;
    let routeLayer;

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return (match && match[1]) || config.csrfToken;
    }

    function setNote(text) {
        noteNode.textContent = text;
    }

    function renderRoute(driverLat, driverLng, userLat, userLng, hospLat, hospLng) {
        if (!driverLat || !driverLng || !userLat || !userLng || !hospLat || !hospLng) {
            return;
        }

        fetch(`https://router.project-osrm.org/route/v1/driving/${driverLng},${driverLat};${userLng},${userLat};${hospLng},${hospLat}?overview=full&geometries=geojson`)
            .then((response) => response.json())
            .then((data) => {
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
            });
    }

    function updateMarker(marker, lat, lng, label) {
        if (lat == null || lng == null) {
            return marker;
        }

        if (marker) {
            marker.setLatLng([lat, lng]);
            return marker;
        }

        return L.marker([lat, lng]).addTo(map).bindPopup(label);
    }

    function postUserLocation(lat, lng) {
        const body = new URLSearchParams({
            lat,
            lon: lng,
        });

        return fetch(config.updateLocationUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": getCsrfToken(),
                "X-Requested-With": "XMLHttpRequest",
            },
            body,
        });
    }

    function refreshStatus() {
        fetch(config.statusUrl, {
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then((response) => response.json())
            .then((data) => {
                statusNode.textContent = data.status;
                driverNode.textContent = data.driver_name;
                hospitalNode.textContent = data.hospital_name;

                driverMarker = updateMarker(driverMarker, data.driver_lat, data.driver_lng, `Driver: ${data.driver_name}`);
                hospitalMarker = updateMarker(hospitalMarker, data.hospital_lat, data.hospital_lng, `Hospital: ${data.hospital_name}`);
                userMarker = updateMarker(userMarker, data.pickup_lat, data.pickup_lng, `You: booking #${bookingId}`);

                renderRoute(data.driver_lat, data.driver_lng, data.pickup_lat, data.pickup_lng, data.hospital_lat, data.hospital_lng);

                if (data.status === "completed") {
                    setNote("Trip completed. The final route is shown on the map.");
                } else {
                    setNote("Live rider location is pinging while the driver approaches.");
                }
            });
    }

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    userMarker = updateMarker(userMarker, pickupLat, pickupLng, `You: booking #${bookingId}`);
    driverMarker = updateMarker(driverMarker, initialDriverLat, initialDriverLng, "Driver");
    hospitalMarker = updateMarker(hospitalMarker, hospitalLat, hospitalLng, "Hospital");
    renderRoute(initialDriverLat, initialDriverLng, pickupLat, pickupLng, hospitalLat, hospitalLng);

    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(
            (position) => {
                const lat = Number(position.coords.latitude.toFixed(5));
                const lng = Number(position.coords.longitude.toFixed(5));

                userMarker = updateMarker(userMarker, lat, lng, `You: booking #${bookingId}`);
                postUserLocation(lat, lng);
                setNote("Your live pickup position was updated for dispatch.");
            },
            () => setNote("Location permission was denied, so the last saved pickup point is being used."),
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
        );
    }

    refreshStatus();
    window.setInterval(refreshStatus, 10000);
})();
