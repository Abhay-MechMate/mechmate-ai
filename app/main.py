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

from app.diagnostic_engine import run_diagnostic


app = FastAPI(title="MechMate AI")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Create database tables when the website starts
init_db()

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
    selected_vehicle = None

    if vehicle_id > 0:
       selected_vehicle = get_vehicle(vehicle_id)

    result, input_text = run_diagnostic(
       obd_code=obd_code,
       symptom=symptom,
       vehicle=selected_vehicle,
)
    add_diagnostic_session(
        vehicle_id=vehicle_id if selected_vehicle else None,
        input_text=input_text,
        summary=result["summary"],
        severity=result["severity"],
        causes=result["causes"],
        inspection=result["inspection"],
        parts=result["parts"],
        safety=result["safety"],
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

