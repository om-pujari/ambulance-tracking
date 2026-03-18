/* Booking flow controller for the cascading rider modals. */
(function () {
    const config = window.bookingConfig;
    if (!config) {
        return;
    }

    const state = {
        phone: "",
        ambulanceType: "",
        hospitalPreference: "",
        lat: null,
        lon: null,
    };

    const message = document.getElementById("booking-message");
    const resultText = document.getElementById("booking-result-text");
    const trackingLink = document.getElementById("tracking-link");
    const modals = Array.from(document.querySelectorAll(".flow-modal"));
    const phoneForm = document.getElementById("phone-form");
    const otpForm = document.getElementById("otp-form");
    const ambulanceOptions = document.getElementById("ambulance-options");
    const hospitalOptions = document.getElementById("hospital-options");

    function setMessage(text, tone) {
        message.textContent = text || "";
        message.className = "form-message";
        if (tone) {
            message.classList.add(tone);
        }
    }

    function showStep(stepNumber) {
        modals.forEach((modal) => {
            modal.classList.toggle("is-active", modal.dataset.step === String(stepNumber));
        });
    }

    function postForm(url, payload) {
        const body = new URLSearchParams(payload);
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

    function requestLocation() {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve({ lat: 0, lon: 0 });
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        lat: position.coords.latitude.toFixed(5),
                        lon: position.coords.longitude.toFixed(5),
                    });
                },
                () => resolve({ lat: 0, lon: 0 }),
                { enableHighAccuracy: true, timeout: 10000 }
            );
        });
    }

    phoneForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        state.phone = document.getElementById("booking-phone").value.trim();
        setMessage("Sending OTP...");

        const response = await postForm(config.urls.sendOtp, { phone: state.phone });
        if (response.status === "sent") {
            setMessage("OTP sent. Check the development console for the code.", "success");
            showStep(2);
            return;
        }
        setMessage("Unable to send OTP right now.", "error");
    });

    otpForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const code = document.getElementById("otp-code").value.trim();
        setMessage("Verifying OTP...");

        const response = await postForm(config.urls.verifyOtp, {
            phone: state.phone,
            code,
        });

        if (response.status === "verified") {
            setMessage("Phone verified.", "success");
            showStep(3);
            return;
        }
        setMessage("Invalid OTP. Please try again.", "error");
    });

    ambulanceOptions.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-ambulance]");
        if (!button) {
            return;
        }

        state.ambulanceType = button.dataset.ambulance;
        ambulanceOptions.querySelectorAll(".selection-card").forEach((card) => card.classList.remove("selected"));
        button.classList.add("selected");
        setMessage("Saving ambulance type...");

        const response = await postForm(config.urls.saveAmbulance, {
            ambulance_type: state.ambulanceType,
        });

        if (response.status === "saved") {
            setMessage("Ambulance type saved.", "success");
            showStep(4);
            return;
        }
        setMessage("Unable to save ambulance type.", "error");
    });

    hospitalOptions.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-hospital]");
        if (!button) {
            return;
        }

        hospitalOptions.querySelectorAll(".selection-card").forEach((card) => card.classList.remove("selected"));
        button.classList.add("selected");
        state.hospitalPreference = button.dataset.hospital;
        setMessage("Capturing location and creating booking...");

        const coords = await requestLocation();
        state.lat = coords.lat;
        state.lon = coords.lon;

        const response = await postForm(config.urls.createBooking, {
            hospital_pref: state.hospitalPreference,
            ambulance_type: state.ambulanceType,
            lat: state.lat,
            lon: state.lon,
        });

        if (response.status === "created") {
            resultText.textContent = `Booking #${response.booking_id} created for ${response.ambulance_type}. Current status: ${response.booking_status}.`;
            trackingLink.href = response.tracking_url || trackingLink.href;
            setMessage("Booking created successfully.", "success");
            showStep(5);
            window.setTimeout(() => {
                if (response.tracking_url) {
                    window.location.href = response.tracking_url;
                }
            }, 1200);
            return;
        }
        setMessage(response.message || "Booking could not be created.", "error");
    });

    showStep(1);
})();


