function appendOptions(dataList, values) {
    dataList.replaceChildren();
    values.forEach(function (value) {
        const option = document.createElement("option");
        option.value = value;
        dataList.appendChild(option);
    });
}

function setupVehicleYearDropdown(yearSelect) {
    if (!yearSelect) {
        return;
    }

    const newestModelYear = new Date().getFullYear() + 1;
    for (let year = newestModelYear; year >= 1981; year -= 1) {
        const option = document.createElement("option");
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
}

function setupVehicleLookup() {
    const yearSelect = document.getElementById("vehicleYear");
    const makeInput = document.getElementById("vehicleMake");
    const modelInput = document.getElementById("vehicleModel");
    const engineInput = document.getElementById("vehicleEngine");
    const vinInput = document.getElementById("vehicleVin");
    const decodeButton = document.getElementById("decodeVinButton");
    const makeOptions = document.getElementById("vehicleMakeOptions");
    const modelOptions = document.getElementById("vehicleModelOptions");
    const status = document.getElementById("vehicleLookupStatus");

    if (!yearSelect || !makeInput || !modelInput || !engineInput || !vinInput || !decodeButton || !makeOptions || !modelOptions || !status) {
        return;
    }

    setupVehicleYearDropdown(yearSelect);

    let availableMakes = [];
    let lastLoadedMake = "";

    function setStatus(message, isError) {
        status.textContent = message;
        status.classList.toggle("lookup-error", Boolean(isError));
    }

    async function getLookupJson(url) {
        const response = await fetch(url, { headers: { Accept: "application/json" } });
        if (!response.ok) {
            throw new Error("Vehicle lookup request failed.");
        }
        return response.json();
    }

    async function loadMakes() {
        const year = yearSelect.value;
        appendOptions(makeOptions, []);
        appendOptions(modelOptions, []);
        modelInput.value = "";
        availableMakes = [];
        lastLoadedMake = "";

        if (!year) {
            modelInput.placeholder = "Choose or type a model";
            return;
        }

        setStatus("Loading NHTSA makes…", false);
        try {
            const payload = await getLookupJson(`/api/vehicles/makes?year=${encodeURIComponent(year)}`);
            availableMakes = Array.isArray(payload.makes) ? payload.makes : [];
            appendOptions(makeOptions, availableMakes);
            setStatus(payload.error || (availableMakes.length ? "" : "No makes returned. You can type a make manually."), Boolean(payload.error));
        } catch (error) {
            setStatus("Vehicle lookup is unavailable. You can type a make and model manually.", true);
        }
    }

    function selectedNhtsaMake() {
        const enteredMake = makeInput.value.trim();
        return availableMakes.find(function (make) {
            return make.toLowerCase() === enteredMake.toLowerCase();
        }) || "";
    }

    async function loadModels() {
        const year = yearSelect.value;
        const make = selectedNhtsaMake();
        appendOptions(modelOptions, []);

        if (!year || !make) {
            modelInput.placeholder = "Choose or type a model";
            return;
        }
        if (lastLoadedMake === `${year}:${make}`) {
            return;
        }

        lastLoadedMake = `${year}:${make}`;
        setStatus("Loading NHTSA models…", false);
        try {
            const payload = await getLookupJson(`/api/vehicles/models?year=${encodeURIComponent(year)}&make=${encodeURIComponent(make)}`);
            const models = Array.isArray(payload.models) ? payload.models : [];
            appendOptions(modelOptions, models);
            modelInput.placeholder = models.length ? "Choose or type a model" : "Type a model manually";
            setStatus(payload.error || (models.length ? "" : "No models returned. You can type a model manually."), Boolean(payload.error));
        } catch (error) {
            setStatus("Vehicle lookup is unavailable. You can type a model manually.", true);
        }
    }

    async function decodeVin() {
        const vin = vinInput.value.trim().toUpperCase();
        if (!vin) {
            setStatus("Enter a VIN to decode it.", true);
            return;
        }

        decodeButton.disabled = true;
        setStatus("Decoding VIN with NHTSA…", false);
        try {
            const payload = await getLookupJson(`/api/vehicles/decode-vin?vin=${encodeURIComponent(vin)}`);
            if (!payload.vehicle) {
                setStatus(payload.error || "NHTSA could not decode this VIN. Enter vehicle details manually.", true);
                return;
            }

            const vehicle = payload.vehicle;
            if (vehicle.year) {
                yearSelect.value = String(vehicle.year);
                await loadMakes();
            }
            if (vehicle.make) {
                makeInput.value = vehicle.make;
                await loadModels();
            }
            if (vehicle.model) {
                modelInput.value = vehicle.model;
            }
            if (vehicle.engine) {
                engineInput.value = vehicle.engine;
            }
            setStatus(payload.error || "VIN decoded. Review the auto-filled details before saving.", Boolean(payload.error));
        } catch (error) {
            setStatus("VIN decoding is unavailable. Enter vehicle details manually.", true);
        } finally {
            decodeButton.disabled = false;
        }
    }

    yearSelect.addEventListener("change", loadMakes);
    makeInput.addEventListener("input", function () {
        lastLoadedMake = "";
        if (selectedNhtsaMake()) {
            loadModels();
        } else {
            appendOptions(modelOptions, []);
        }
    });
    decodeButton.addEventListener("click", decodeVin);
}

function setupIntakeVehiclePreview() {
    const vehicleSelect = document.getElementById("intakeVehicle");
    const preview = document.getElementById("intakeVehiclePreview");

    if (!vehicleSelect || !preview) {
        return;
    }

    function updatePreview() {
        const selectedOption = vehicleSelect.options[vehicleSelect.selectedIndex];
        preview.textContent = selectedOption ? selectedOption.dataset.vehicleSummary : "";
    }

    vehicleSelect.addEventListener("change", updatePreview);
    updatePreview();
}

setupVehicleLookup();
setupIntakeVehiclePreview();
