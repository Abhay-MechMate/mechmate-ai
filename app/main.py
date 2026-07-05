from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import (
    init_db,
    add_vehicle,
    get_vehicles,
    get_vehicle,
    add_diagnostic_session,
    get_diagnostic_history,
)


app = FastAPI(title="MechMate AI")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Create database tables when the website starts
init_db()


OBD_DATABASE = {
    "P0301": {
        "summary": "P0301 means cylinder 1 misfire detected.",
        "severity": "Medium to High",
        "causes": [
            "Bad cylinder 1 spark plug",
            "Faulty cylinder 1 ignition coil",
            "Fuel injector issue",
            "Vacuum leak",
            "Low compression on cylinder 1",
        ],
        "inspection": [
            "Inspect cylinder 1 spark plug.",
            "Swap cylinder 1 ignition coil with another cylinder and see if the misfire follows.",
            "Listen for injector operation.",
            "Check for vacuum leaks.",
            "Perform compression test if the misfire remains.",
        ],
        "parts": [
            "Spark plug",
            "Ignition coil",
            "OBD-II scanner",
            "Compression tester",
        ],
        "safety": "Avoid hard driving if the check engine light is flashing because misfires can damage the catalytic converter.",
    },
    "P0420": {
        "summary": "P0420 means catalyst system efficiency is below threshold.",
        "severity": "Medium",
        "causes": [
            "Failing catalytic converter",
            "Aging oxygen sensor",
            "Exhaust leak",
            "Previous misfire damage",
        ],
        "inspection": [
            "Check for exhaust leaks before the catalytic converter.",
            "Review oxygen sensor data with a scan tool.",
            "Check for misfire or fuel trim problems.",
            "Inspect catalytic converter condition.",
        ],
        "parts": [
            "Oxygen sensor",
            "Catalytic converter",
            "Exhaust repair parts",
            "Scan tool",
        ],
        "safety": "Do not ignore misfires or rich-running conditions because they can overheat the catalytic converter.",
    },
    "P0171": {
        "summary": "P0171 means the engine is running too lean on bank 1.",
        "severity": "Medium",
        "causes": [
            "Vacuum leak",
            "Dirty or faulty MAF sensor",
            "Weak fuel pump",
            "Clogged fuel injector",
            "Exhaust leak before oxygen sensor",
        ],
        "inspection": [
            "Check intake hoses for cracks.",
            "Inspect vacuum lines.",
            "Clean or inspect MAF sensor.",
            "Review fuel trim data.",
            "Check fuel pressure if needed.",
        ],
        "parts": [
            "MAF cleaner",
            "Vacuum hose",
            "Fuel pressure tester",
            "Scan tool",
        ],
        "safety": "A lean condition can cause rough running and higher combustion temperatures if ignored.",
    },
}


def diagnose_symptom(symptom: str):
    symptom_lower = symptom.lower()

    if "brake" in symptom_lower or "shaking" in symptom_lower or "vibration" in symptom_lower:
        return {
            "summary": "A shaking or vibration while braking is commonly related to the brake or front suspension system.",
            "severity": "Medium",
            "causes": [
                "Warped brake rotors",
                "Uneven brake pad deposits",
                "Worn brake pads",
                "Loose suspension component",
                "Wheel or tire issue",
            ],
            "inspection": [
                "Inspect front brake rotor condition.",
                "Check brake pad thickness.",
                "Check rotor runout if tools are available.",
                "Inspect tie rods, ball joints, and control arms.",
                "Check wheel balance if vibration happens even without braking.",
            ],
            "parts": [
                "Brake pads",
                "Brake rotors",
                "Brake cleaner",
                "Jack and jack stands",
                "Torque wrench",
            ],
            "safety": "Brake vibration should be inspected soon because braking performance affects safety.",
        }

    if "overheat" in symptom_lower or "hot" in symptom_lower or "coolant" in symptom_lower:
        return {
            "summary": "Overheating can come from low coolant, airflow issues, thermostat problems, or water pump issues.",
            "severity": "High",
            "causes": [
                "Low coolant",
                "Stuck thermostat",
                "Radiator fan problem",
                "Water pump issue",
                "Coolant leak",
            ],
            "inspection": [
                "Check coolant level only when the engine is cold.",
                "Look for coolant leaks.",
                "Verify radiator fan operation.",
                "Monitor coolant temperature.",
                "Inspect thermostat operation.",
            ],
            "parts": [
                "Coolant",
                "Thermostat",
                "Radiator cap",
                "Cooling system pressure tester",
            ],
            "safety": "Do not open the radiator cap when hot. Overheating can damage the engine quickly.",
        }

    return {
        "summary": "This symptom needs more information, but MechMate AI can suggest a basic inspection path.",
        "severity": "Unknown",
        "causes": [
            "Wear item issue",
            "Sensor issue",
            "Fluid level issue",
            "Mechanical fault",
            "Electrical issue",
        ],
        "inspection": [
            "Scan the vehicle for OBD-II codes.",
            "Check fluid levels.",
            "Listen for abnormal sounds.",
            "Inspect visible leaks or damaged parts.",
            "Document when the issue happens.",
        ],
        "parts": [
            "OBD-II scanner",
            "Flashlight",
            "Basic hand tools",
            "Notebook or phone for notes",
        ],
        "safety": "If the issue affects braking, steering, overheating, or engine misfire, inspect it before driving aggressively.",
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {}
    )


@app.get("/vehicles", response_class=HTMLResponse)
def vehicles_page(request: Request):
    vehicles = get_vehicles()

    return templates.TemplateResponse(
        request,
        "vehicles.html",
        {"vehicles": vehicles}
    )


@app.post("/vehicles", response_class=HTMLResponse)
def add_vehicle_page(
    request: Request,
    year: int = Form(...),
    make: str = Form(...),
    model: str = Form(...),
    mileage: int = Form(...),
    engine: str = Form("")
):
    add_vehicle(
        year=year,
        make=make,
        model=model,
        mileage=mileage,
        engine=engine,
    )

    vehicles = get_vehicles()

    return templates.TemplateResponse(
        request,
        "vehicles.html",
        {
            "vehicles": vehicles,
            "message": "Vehicle saved successfully."
        }
    )


@app.get("/diagnose", response_class=HTMLResponse)
def diagnose_page(request: Request):
    vehicles = get_vehicles()

    return templates.TemplateResponse(
        request,
        "diagnose.html",
        {
            "vehicles": vehicles,
            "result": None
        }
    )


@app.post("/diagnose", response_class=HTMLResponse)
def run_diagnosis(
    request: Request,
    vehicle_id: int = Form(0),
    obd_code: str = Form(""),
    symptom: str = Form("")
):
    obd_code = obd_code.strip().upper()
    symptom = symptom.strip()

    if obd_code and obd_code in OBD_DATABASE:
        result = OBD_DATABASE[obd_code]
        input_text = obd_code
    elif symptom:
        result = diagnose_symptom(symptom)
        input_text = symptom
    else:
        result = {
            "summary": "Please enter an OBD-II code or symptom.",
            "severity": "Unknown",
            "causes": [],
            "inspection": [],
            "parts": [],
            "safety": "No diagnostic input was provided.",
        }
        input_text = "No input"

    selected_vehicle = None

    if vehicle_id > 0:
        selected_vehicle = get_vehicle(vehicle_id)

    add_diagnostic_session(
        vehicle_id=vehicle_id if selected_vehicle else None,
        input_text=input_text,
        summary=result["summary"],
        severity=result["severity"],
    )

    vehicles = get_vehicles()

    return templates.TemplateResponse(
        request,
        "diagnose.html",
        {
            "vehicles": vehicles,
            "result": result,
            "input_text": input_text,
            "selected_vehicle": selected_vehicle,
        }
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    history = get_diagnostic_history()

    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "history": history
        }
    )