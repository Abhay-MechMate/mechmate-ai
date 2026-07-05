const vehicleModelsByMake = {
    "Toyota": [
        "GR86",
        "Corolla",
        "Camry",
        "Prius",
        "RAV4",
        "Highlander",
        "Tacoma",
        "Tundra",
        "4Runner",
        "Sienna",
        "Supra",
        "Other / Not Listed"
    ],

    "Honda": [
        "Civic",
        "Accord",
        "CR-V",
        "HR-V",
        "Pilot",
        "Odyssey",
        "Ridgeline",
        "Fit",
        "Passport",
        "Other / Not Listed"
    ],

    "Subaru": [
        "BRZ",
        "WRX",
        "Impreza",
        "Legacy",
        "Outback",
        "Crosstrek",
        "Forester",
        "Ascent",
        "Other / Not Listed"
    ],

    "Ford": [
        "F-150",
        "F-250",
        "F-350",
        "Ranger",
        "Maverick",
        "Bronco",
        "Explorer",
        "Escape",
        "Edge",
        "Mustang",
        "Transit",
        "Other / Not Listed"
    ],

    "Chevrolet": [
        "Silverado 1500",
        "Silverado 2500HD",
        "Colorado",
        "Tahoe",
        "Suburban",
        "Equinox",
        "Traverse",
        "Malibu",
        "Camaro",
        "Corvette",
        "Other / Not Listed"
    ],

    "GMC": [
        "Sierra 1500",
        "Sierra 2500HD",
        "Canyon",
        "Terrain",
        "Acadia",
        "Yukon",
        "Yukon XL",
        "Other / Not Listed"
    ],

    "Jeep": [
        "Wrangler",
        "Grand Cherokee",
        "Cherokee",
        "Compass",
        "Renegade",
        "Gladiator",
        "Wagoneer",
        "Other / Not Listed"
    ],

    "Nissan": [
        "Altima",
        "Sentra",
        "Maxima",
        "Rogue",
        "Murano",
        "Pathfinder",
        "Frontier",
        "Titan",
        "370Z",
        "Z",
        "GT-R",
        "Other / Not Listed"
    ],

    "Hyundai": [
        "Elantra",
        "Sonata",
        "Accent",
        "Kona",
        "Tucson",
        "Santa Fe",
        "Palisade",
        "Veloster",
        "Genesis Coupe",
        "Other / Not Listed"
    ],

    "Kia": [
        "Forte",
        "K5",
        "Optima",
        "Soul",
        "Sportage",
        "Sorento",
        "Telluride",
        "Stinger",
        "Other / Not Listed"
    ],

    "Mazda": [
        "Mazda3",
        "Mazda6",
        "CX-3",
        "CX-30",
        "CX-5",
        "CX-50",
        "CX-9",
        "MX-5 Miata",
        "RX-8",
        "Other / Not Listed"
    ],

    "BMW": [
        "2 Series",
        "3 Series",
        "4 Series",
        "5 Series",
        "7 Series",
        "X1",
        "X3",
        "X5",
        "M2",
        "M3",
        "M4",
        "Other / Not Listed"
    ],

    "Mercedes-Benz": [
        "A-Class",
        "C-Class",
        "E-Class",
        "S-Class",
        "CLA",
        "GLA",
        "GLC",
        "GLE",
        "GLS",
        "AMG GT",
        "Other / Not Listed"
    ],

    "Audi": [
        "A3",
        "A4",
        "A5",
        "A6",
        "A7",
        "A8",
        "Q3",
        "Q5",
        "Q7",
        "Q8",
        "S4",
        "RS3",
        "RS5",
        "Other / Not Listed"
    ],

    "Lexus": [
        "IS",
        "ES",
        "GS",
        "LS",
        "RC",
        "LC",
        "UX",
        "NX",
        "RX",
        "GX",
        "LX",
        "Other / Not Listed"
    ],

    "Volkswagen": [
        "Jetta",
        "Passat",
        "Golf",
        "GTI",
        "Golf R",
        "Beetle",
        "Tiguan",
        "Atlas",
        "Arteon",
        "Other / Not Listed"
    ],

    "Other / Not Listed": [
        "Other / Not Listed"
    ]
};

function setupVehicleYearDropdown() {
    const yearSelect = document.getElementById("vehicleYear");

    if (!yearSelect) {
        return;
    }

    const currentYear = new Date().getFullYear() + 1;
    const oldestYear = 1980;

    for (let year = currentYear; year >= oldestYear; year--) {
        const option = document.createElement("option");
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
}

function setupVehicleModelDropdown() {
    const makeSelect = document.getElementById("vehicleMake");
    const modelSelect = document.getElementById("vehicleModel");

    if (!makeSelect || !modelSelect) {
        return;
    }

    makeSelect.addEventListener("change", function () {
        const selectedMake = makeSelect.value;
        const models = vehicleModelsByMake[selectedMake] || [];

        modelSelect.innerHTML = "";

        if (!selectedMake) {
            modelSelect.disabled = true;

            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Select make first";
            modelSelect.appendChild(option);

            return;
        }

        modelSelect.disabled = false;

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Select model";
        modelSelect.appendChild(defaultOption);

        models.forEach(function (model) {
            const option = document.createElement("option");
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });
    });
}

setupVehicleYearDropdown();
setupVehicleModelDropdown();