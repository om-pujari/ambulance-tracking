/* Admin dashboard controller for fleet tracking and booking heatmap. */
(function () {
    const driversNode = document.getElementById("admin-drivers-data");
    const bookingsNode = document.getElementById("admin-bookings-data");
    if (!driversNode || !bookingsNode || !window.L) {
        return;
    }

    const drivers = JSON.parse(driversNode.textContent);
    const bookings = JSON.parse(bookingsNode.textContent);
    const defaultCenter = [20.5937, 78.9629];

    function createMap(id, zoom) {
        const map = L.map(id).setView(defaultCenter, zoom);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        return map;
    }

    function fitMapToPoints(map, points) {
        if (!points.length) {
            return;
        }
        map.fitBounds(points, { padding: [30, 30] });
    }

    const fleetMap = createMap("fleet-map", 5);
    const heatMap = createMap("heatmap", 5);
    const fleetPoints = [];
    const bookingPoints = [];

    drivers.forEach((driver) => {
        if (driver.lat == null || driver.lng == null) {
            return;
        }
        const point = [driver.lat, driver.lng];
        fleetPoints.push(point);
        L.circleMarker(point, {
            radius: 8,
            color: driver.state === "On" ? "#0e8f67" : "#e14942",
            fillOpacity: 0.8,
        })
            .addTo(fleetMap)
            .bindPopup(`${driver.name}<br>${driver.ambulance_type}<br>${driver.state}`);
    });

    bookings.forEach((booking) => {
        if (booking.lat == null || booking.lng == null) {
            return;
        }
        bookingPoints.push([booking.lat, booking.lng, 0.9]);
        L.circleMarker([booking.lat, booking.lng], {
            radius: 5,
            color: "#e14942",
            fillOpacity: 0.35,
        })
            .addTo(heatMap)
            .bindPopup(`${booking.ambulance_type}<br>${booking.status}`);
    });

    if (window.L.heatLayer && bookingPoints.length) {
        L.heatLayer(bookingPoints, {
            radius: 28,
            blur: 20,
            maxZoom: 16,
        }).addTo(heatMap);
    }

    fitMapToPoints(fleetMap, fleetPoints);
    fitMapToPoints(heatMap, bookingPoints.map((entry) => [entry[0], entry[1]]));
})();
