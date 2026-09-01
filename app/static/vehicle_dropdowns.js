const vehicleModelsByMake = {
    Acura: ["ILX", "Integra", "MDX", "RDX", "TLX"],
    "Alfa Romeo": ["Giulia", "Stelvio", "Tonale"],
    Audi: ["A3", "A4", "A5", "A6", "A7", "A8", "Q3", "Q5", "Q7", "Q8", "RS 3", "RS 5", "S4"],
    BMW: ["2 Series", "3 Series", "4 Series", "5 Series", "7 Series", "M2", "M3", "M4", "X1", "X3", "X5", "X7"],
    Buick: ["Enclave", "Encore", "Envision", "Envista"],
    Cadillac: ["CT4", "CT5", "Escalade", "LYRIQ", "XT4", "XT5", "XT6"],
    Chevrolet: ["Blazer", "Colorado", "Corvette", "Equinox", "Malibu", "Silverado 1500", "Silverado 2500HD", "Suburban", "Tahoe", "Traverse", "Trax"],
    Chrysler: ["300", "Pacifica", "Voyager"],
    Dodge: ["Challenger", "Charger", "Durango", "Hornet"],
    Ford: ["Bronco", "Escape", "Explorer", "F-150", "Maverick", "Mustang", "Ranger", "Super Duty", "Transit"],
    Genesis: ["G70", "G80", "G90", "GV60", "GV70", "GV80"],
    GMC: ["Acadia", "Canyon", "Hummer EV", "Sierra 1500", "Terrain", "Yukon"],
    Honda: ["Accord", "Civic", "CR-V", "HR-V", "Odyssey", "Passport", "Pilot", "Ridgeline"],
    Hyundai: ["Elantra", "Ioniq 5", "Kona", "Palisade", "Santa Cruz", "Santa Fe", "Sonata", "Tucson"],
    Infiniti: ["Q50", "QX50", "QX55", "QX60", "QX80"],
    Jeep: ["Compass", "Gladiator", "Grand Cherokee", "Grand Wagoneer", "Renegade", "Wagoneer", "Wrangler"],
    Kia: ["Carnival", "EV6", "Forte", "K5", "Niro", "Seltos", "Sorento", "Soul", "Sportage", "Telluride"],
    Lexus: ["ES", "GX", "IS", "LC", "LS", "LX", "NX", "RX", "TX", "UX"],
    Lincoln: ["Aviator", "Corsair", "Nautilus", "Navigator"],
    Mazda: ["CX-30", "CX-5", "CX-50", "CX-90", "Mazda3", "MX-5 Miata"],
    "Mercedes-Benz": ["C-Class", "CLA", "CLE", "E-Class", "EQE", "EQS", "GLA", "GLC", "GLE", "GLS", "S-Class"],
    Mini: ["Clubman", "Convertible", "Countryman", "Hardtop"],
    Mitsubishi: ["Eclipse Cross", "Mirage", "Outlander", "Outlander PHEV"],
    Nissan: ["Altima", "Ariya", "Frontier", "Kicks", "Leaf", "Murano", "Pathfinder", "Rogue", "Sentra", "Versa", "Z"],
    Porsche: ["718", "911", "Cayenne", "Macan", "Panamera", "Taycan"],
    Ram: ["1500", "2500", "3500", "ProMaster"],
    Subaru: ["Ascent", "BRZ", "Crosstrek", "Forester", "Impreza", "Legacy", "Outback", "Solterra", "WRX"],
    Tesla: ["Cybertruck", "Model 3", "Model S", "Model X", "Model Y"],
    Toyota: ["4Runner", "Camry", "Corolla", "GR86", "Grand Highlander", "Highlander", "Prius", "RAV4", "Sequoia", "Sienna", "Supra", "Tacoma", "Tundra"],
    Volkswagen: ["Atlas", "Golf", "Golf R", "GTI", "ID.4", "Jetta", "Taos", "Tiguan"],
    Volvo: ["C40 Recharge", "EX30", "EX90", "S60", "V60", "XC40", "XC60", "XC90"]
};

function appendOptions(dataList, values) {
    dataList.replaceChildren();
    values.forEach(function (value) {
        const option = document.createElement("option");
        option.value = value;
        dataList.appendChild(option);
    });
}

function setupVehicleYearDropdown() {
    const yearSelect = document.getElementById("vehicleYear");

    if (!yearSelect) {
        return;
    }

    const newestModelYear = new Date().getFullYear() + 1;
    for (let year = newestModelYear; year >= 1980; year -= 1) {
        const option = document.createElement("option");
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
}

function setupVehicleMakeAndModelInputs() {
    const makeInput = document.getElementById("vehicleMake");
    const modelInput = document.getElementById("vehicleModel");
    const makeOptions = document.getElementById("vehicleMakeOptions");
    const modelOptions = document.getElementById("vehicleModelOptions");

    if (!makeInput || !modelInput || !makeOptions || !modelOptions) {
        return;
    }

    const makes = Object.keys(vehicleModelsByMake).sort(function (first, second) {
        return first.localeCompare(second);
    });
    appendOptions(makeOptions, makes);

    function updateModelSuggestions() {
        const matchingMake = makes.find(function (make) {
            return make.toLowerCase() === makeInput.value.trim().toLowerCase();
        });
        const models = matchingMake ? vehicleModelsByMake[matchingMake] : [];
        appendOptions(modelOptions, [...models].sort(function (first, second) {
            return first.localeCompare(second, undefined, { numeric: true });
        }));
        modelInput.placeholder = matchingMake
            ? "Choose or type a model"
            : "Type a model or choose a listed make first";
    }

    makeInput.addEventListener("input", updateModelSuggestions);
    updateModelSuggestions();
}

setupVehicleYearDropdown();
setupVehicleMakeAndModelInputs();
