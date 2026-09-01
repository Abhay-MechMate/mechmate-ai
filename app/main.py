import hmac
import os
import re
from datetime import date
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
    create_session_token,
    get_session_user_id,
    hash_password,
    verify_password,
)
from app.database import (
    add_customer_case,
    add_diagnostic_session,
    add_knowledge_item,
    add_user,
    add_vehicle,
    get_diagnostic_history,
    get_customer_case,
    get_customer_cases,
    get_dashboard_stats,
    get_knowledge_items,
    get_recent_dashboard_items,
    get_store_options,
    get_user_by_email,
    get_user_by_id,
    get_vehicle,
    get_vehicles,
    init_db,
    search_knowledge_items,
    update_customer_case_follow_up_status,
)
from app.ai_client import generate_ai_diagnosis, is_ai_diagnostics_enabled
from app.diagnostic_engine import run_diagnostic


app = FastAPI(title="MechMate AI")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

FOLLOW_UP_STATUSES = [
    "not needed",
    "not contacted",
    "ready for follow-up",
    "contacted",
    "resolved",
]

DEMO_VEHICLE = {
    "year": 2021,
    "make": "Honda",
    "model": "Civic",
    "mileage": 48500,
    "engine": "2.0L I4",
}
DEMO_DIAGNOSTIC_INPUT = "Demo data: P0301 cylinder one misfire"
DEMO_CUSTOMER_NAME = "Demo Customer"
DEMO_CASE_COMPLAINT = "Rough idle with OBD-II code P0301"
NHTSA_VPIC_BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"
NHTSA_MAKES_CACHE: dict[int, list[str]] = {}
NHTSA_MODELS_CACHE: dict[tuple[int, str], list[str]] = {}

# Create database tables when the website starts.
init_db()


class VoiceDiagnosticRequest(BaseModel):
    year: int | None = None
    make: str | None = None
    model: str | None = None
    mileage: int | None = None
    engine: str | None = None
    obd_code: str | None = None
    symptom: str | None = None


def get_current_user(request: Request):
    user_id = get_session_user_id(request.cookies.get(SESSION_COOKIE_NAME))
    return get_user_by_id(user_id) if user_id else None


def render_template(request: Request, name: str, context: dict | None = None):
    return templates.TemplateResponse(
        request,
        name,
        {"current_user": get_current_user(request), **(context or {})},
    )


def redirect_with_session(path: str, user_id: int):
    response = RedirectResponse(path, status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


def redirect_to_login():
    return RedirectResponse("/login", status_code=303)


def build_voice_vehicle(request_data: VoiceDiagnosticRequest):
    vehicle_values = [
        request_data.year,
        request_data.make,
        request_data.model,
        request_data.mileage,
        request_data.engine,
    ]

    if not any(value not in (None, "") for value in vehicle_values):
        return None

    return {
        "year": request_data.year if request_data.year is not None else "not provided",
        "make": request_data.make or "not provided",
        "model": request_data.model or "not provided",
        "mileage": request_data.mileage if request_data.mileage is not None else 0,
        "engine": request_data.engine or "not provided",
    }


def build_spoken_response(result: dict) -> str:
    response_parts = [result["summary"]]
    causes = result.get("causes", [])[:2]
    inspection = result.get("inspection", [])
    safety = result.get("safety")

    if causes:
        response_parts.append(f"Likely causes include {' and '.join(causes)}.")
    if inspection:
        response_parts.append(f"First, {inspection[0]}")
    if safety:
        response_parts.append(f"Safety note: {safety}")

    return " ".join(response_parts)


def is_voice_request_authorized(provided_key: str | None) -> bool:
    configured_key = os.getenv("VOICE_TOOL_API_KEY")

    if not configured_key:
        return True

    return bool(provided_key) and hmac.compare_digest(provided_key, configured_key)


def fetch_nhtsa_json(path: str) -> dict | None:
    """Fetch a JSON response from NHTSA vPIC without exposing it to the browser."""
    try:
        response = httpx.get(
            f"{NHTSA_VPIC_BASE_URL}/{path}",
            params={"format": "json"},
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    return payload if isinstance(payload, dict) else None


def sorted_nhtsa_values(results: list[dict], field_name: str) -> list[str]:
    """Extract, de-duplicate, and alphabetize vPIC text results."""
    values = {
        str(item.get(field_name, "")).strip()
        for item in results
        if isinstance(item, dict) and str(item.get(field_name, "")).strip()
    }
    return sorted(values, key=str.casefold)


def valid_vehicle_year(year: int) -> bool:
    return 1981 <= year <= date.today().year + 1


@app.get("/api/vehicles/makes")
def get_vehicle_makes(year: int):
    if not valid_vehicle_year(year):
        return {"makes": [], "error": "Choose a model year from 1981 through next model year."}

    cached_makes = NHTSA_MAKES_CACHE.get(year)
    if cached_makes is not None:
        return {"makes": cached_makes}

    # vPIC's make list is vehicle-type based. The selected model year is applied
    # by the year-and-make model lookup that follows this request.
    payload = fetch_nhtsa_json("GetMakesForVehicleType/car")
    results = payload.get("Results") if payload else None
    if not isinstance(results, list):
        return {"makes": [], "error": "Vehicle make lookup is temporarily unavailable. Type a make manually."}

    makes = sorted_nhtsa_values(results, "MakeName")
    NHTSA_MAKES_CACHE[year] = makes
    return {"makes": makes}


@app.get("/api/vehicles/models")
def get_vehicle_models(year: int, make: str):
    normalized_make = make.strip()
    if not valid_vehicle_year(year) or not normalized_make:
        return {"models": [], "error": "Choose a valid year and enter a make first."}

    cache_key = (year, normalized_make.casefold())
    cached_models = NHTSA_MODELS_CACHE.get(cache_key)
    if cached_models is not None:
        return {"models": cached_models}

    encoded_make = quote(normalized_make, safe="")
    if year > 1995:
        path = f"GetModelsForMakeYear/make/{encoded_make}/modelyear/{year}"
    else:
        path = f"GetModelsForMake/{encoded_make}"

    payload = fetch_nhtsa_json(path)
    results = payload.get("Results") if payload else None
    if not isinstance(results, list):
        return {"models": [], "error": "Vehicle model lookup is temporarily unavailable. Type a model manually."}

    models = sorted_nhtsa_values(results, "Model_Name")
    NHTSA_MODELS_CACHE[cache_key] = models
    return {"models": models}


@app.get("/api/vehicles/decode-vin")
def decode_vehicle_vin(vin: str):
    normalized_vin = vin.strip().upper()
    if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", normalized_vin):
        return {"vehicle": None, "error": "Enter a valid 17-character VIN to decode it."}

    payload = fetch_nhtsa_json(f"DecodeVinValuesExtended/{normalized_vin}")
    results = payload.get("Results") if payload else None
    decoded_values = results[0] if isinstance(results, list) and results else None
    if not isinstance(decoded_values, dict):
        return {"vehicle": None, "error": "VIN decoding is temporarily unavailable. Enter vehicle details manually."}

    decoded_year = str(decoded_values.get("ModelYear", "")).strip()
    displacement = str(decoded_values.get("DisplacementL", "")).strip()
    cylinders = str(decoded_values.get("EngineCylinders", "")).strip()
    engine_parts = [
        f"{displacement}L" if displacement else "",
        f"{cylinders} cylinders" if cylinders else "",
        str(decoded_values.get("EngineModel", "")).strip(),
        str(decoded_values.get("FuelTypePrimary", "")).strip(),
    ]
    vehicle = {
        "year": int(decoded_year) if decoded_year.isdigit() and valid_vehicle_year(int(decoded_year)) else None,
        "make": str(decoded_values.get("Make", "")).strip(),
        "model": str(decoded_values.get("Model", "")).strip(),
        "engine": ", ".join(part for part in engine_parts if part),
    }
    error_text = str(decoded_values.get("ErrorText", "")).strip()
    error_code = str(decoded_values.get("ErrorCode", "")).strip()
    decode_error = error_text if error_code not in ("", "0") else None
    if not any((vehicle["year"], vehicle["make"], vehicle["model"])):
        return {
            "vehicle": None,
            "error": decode_error or "NHTSA could not identify this VIN. Enter vehicle details manually.",
        }

    return {"vehicle": vehicle, "error": decode_error}


def run_diagnostic_with_knowledge(
    obd_code: str,
    symptom: str,
    vehicle: dict | None,
):
    knowledge_matches = []
    knowledge_item = None
    if not obd_code.strip() and symptom.strip():
        knowledge_matches = search_knowledge_items(symptom)
        knowledge_item = knowledge_matches[0] if knowledge_matches else None

    local_result, input_text = run_diagnostic(
        obd_code=obd_code,
        symptom=symptom,
        vehicle=vehicle,
        knowledge_item=knowledge_item,
    )
    ai_result = generate_ai_diagnosis(
        vehicle=vehicle,
        obd_code=obd_code,
        symptom=symptom,
        knowledge_matches=knowledge_matches,
    )

    return (ai_result or local_result), input_text


def split_case_parts_and_tools(items: list[str]) -> tuple[list[str], list[str]]:
    tool_keywords = (
        "scanner",
        "tester",
        "wrench",
        "socket",
        "jack",
        "gauge",
        "flashlight",
        "hand tools",
        "compression",
        "notebook",
    )
    suggested_parts = []
    suggested_tools = []

    for item in items:
        if any(keyword in item.lower() for keyword in tool_keywords):
            suggested_tools.append(item)
        else:
            suggested_parts.append(item)

    return suggested_parts, suggested_tools


def format_case_vehicle(customer_case: dict) -> str:
    """Create a concise vehicle description from a saved customer case."""
    vehicle_details = [
        str(customer_case.get("year") or "").strip(),
        str(customer_case.get("make") or "").strip(),
        str(customer_case.get("model") or "").strip(),
    ]
    vehicle_name = " ".join(part for part in vehicle_details if part)
    return vehicle_name or "the selected vehicle"


def format_case_recommendations(customer_case: dict) -> str:
    """Summarize the saved parts and tools without generating new advice."""
    recommendations = customer_case.get("suggested_parts", []) + customer_case.get(
        "suggested_tools", []
    )
    return ", ".join(recommendations) if recommendations else "the saved inspection guidance"


def build_follow_up_drafts(customer_case: dict) -> dict[str, str]:
    """Build local-only follow-up drafts from an existing customer case."""
    customer_name = customer_case.get("customer_name") or "there"
    vehicle = format_case_vehicle(customer_case)
    complaint = customer_case.get("complaint") or "the reported concern"
    recommendations = format_case_recommendations(customer_case)
    next_step = (
        "review the diagnostic guidance, inspect the vehicle, and confirm the root "
        "cause before replacing parts"
    )
    no_send_notice = "No message has been sent yet."

    return {
        "Text message": (
            f"Hi {customer_name}, this is MechMate AI following up about your {vehicle}. "
            f"You reported: {complaint}. The recommended next step is to {next_step}. "
            f"Suggested parts/tools: {recommendations}. {no_send_notice}"
        ),
        "Email": (
            f"Hello {customer_name},\n\n"
            f"This is a draft follow-up for your {vehicle} regarding: {complaint}. "
            f"The recommended next step is to {next_step}. Suggested parts/tools: "
            f"{recommendations}.\n\n{no_send_notice}"
        ),
        "Voice/phone script": (
            f"Hello {customer_name}. I am following up about your {vehicle} and the concern "
            f"you reported: {complaint}. The recommended next step is to {next_step}. "
            f"The saved suggested parts/tools are {recommendations}. {no_send_notice}"
        ),
        "Syllable agent script": (
            f"Introduce MechMate AI, confirm the customer is {customer_name}, and reference "
            f"their {vehicle}. Restate the complaint: {complaint}. Explain that the recommended "
            f"next step is to {next_step}, with suggested parts/tools of {recommendations}. "
            f"{no_send_notice}"
        ),
    }


def seed_demo_data_for_user(user_id: int) -> None:
    """Create one local diagnostic workflow sample for a user, without duplicates."""
    init_db()
    vehicles = get_vehicles(user_id)
    demo_vehicle = next(
        (
            vehicle
            for vehicle in vehicles
            if all(vehicle.get(field) == value for field, value in DEMO_VEHICLE.items())
        ),
        None,
    )
    if not demo_vehicle:
        vehicle_id = add_vehicle(user_id=user_id, **DEMO_VEHICLE)
        demo_vehicle = get_vehicle(vehicle_id, user_id)

    result, _ = run_diagnostic(
        obd_code="P0301",
        symptom="",
        vehicle=demo_vehicle,
    )
    history = get_diagnostic_history(user_id)
    if not any(item["input_text"] == DEMO_DIAGNOSTIC_INPUT for item in history):
        add_diagnostic_session(
            user_id=user_id,
            vehicle_id=demo_vehicle["id"],
            input_text=DEMO_DIAGNOSTIC_INPUT,
            summary=result["summary"],
            severity=result["severity"],
            causes=result["causes"],
            inspection=result["inspection"],
            parts=result["parts"],
            parts_store_notes=result["parts_store_notes"],
            safety=result["safety"],
        )

    cases = get_customer_cases(user_id)
    if not any(
        customer_case["customer_name"] == DEMO_CUSTOMER_NAME
        and customer_case["complaint"] == DEMO_CASE_COMPLAINT
        for customer_case in cases
    ):
        suggested_parts, suggested_tools = split_case_parts_and_tools(result["parts"])
        add_customer_case(
            user_id=user_id,
            vehicle_id=demo_vehicle["id"],
            customer_name=DEMO_CUSTOMER_NAME,
            customer_email="demo.customer@example.com",
            customer_phone="555-0101",
            complaint=DEMO_CASE_COMPLAINT,
            diagnosis_summary=result["summary"],
            severity=result["severity"],
            suggested_parts=suggested_parts,
            suggested_tools=suggested_tools,
            store_guidance=result["parts_store_notes"],
            follow_up_channel="phone",
            follow_up_status="ready for follow-up",
        )


@app.get("/", response_class=HTMLResponse)
def home(request: Request, demo: str = ""):
    current_user = get_current_user(request)
    if not current_user:
        return render_template(request, "index.html")

    return render_template(
        request,
        "index.html",
        {
            "dashboard_stats": get_dashboard_stats(current_user["id"]),
            "recent_items": get_recent_dashboard_items(current_user["id"]),
            "ai_diagnostics_enabled": is_ai_diagnostics_enabled(),
            "message": "Demo data loaded for this account." if demo == "loaded" else "",
        },
    )


@app.post("/demo/seed")
def seed_demo_data(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    seed_demo_data_for_user(current_user["id"])
    return RedirectResponse("/?demo=loaded", status_code=303)


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return render_template(request, "signup.html")


@app.post("/signup", response_class=HTMLResponse)
def signup(request: Request, email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    email = email.strip().lower()

    if not email or "@" not in email:
        return render_template(request, "signup.html", {"error": "Enter a valid email address.", "email": email})
    if len(password) < 8:
        return render_template(request, "signup.html", {"error": "Use a password with at least 8 characters.", "email": email})
    if password != confirm_password:
        return render_template(request, "signup.html", {"error": "Passwords do not match.", "email": email})

    user_id = add_user(email, hash_password(password))
    if user_id is None:
        return render_template(request, "signup.html", {"error": "An account with that email already exists.", "email": email})

    return redirect_with_session("/", user_id)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return render_template(request, "login.html")


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    user = get_user_by_email(email)

    if not user or not verify_password(password, user["password_hash"]):
        return render_template(request, "login.html", {"error": "Invalid email or password.", "email": email})

    return redirect_with_session("/", user["id"])


@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/cases", response_class=HTMLResponse)
def cases_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    return render_template(
        request,
        "cases.html",
        {"customer_cases": get_customer_cases(current_user["id"])},
    )


@app.get("/cases/new", response_class=HTMLResponse)
def new_case_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    return render_template(
        request,
        "case_new.html",
        {"vehicles": get_vehicles(current_user["id"])},
    )


@app.post("/cases/new", response_class=HTMLResponse)
def create_customer_case(
    request: Request,
    vehicle_id: int = Form(...),
    customer_name: str = Form(""),
    customer_email: str = Form(""),
    customer_phone: str = Form(""),
    complaint: str = Form(""),
    obd_code: str = Form(""),
    follow_up_channel: str = Form("none"),
):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    selected_vehicle = get_vehicle(vehicle_id, current_user["id"])
    if not selected_vehicle:
        return render_template(
            request,
            "case_new.html",
            {
                "vehicles": get_vehicles(current_user["id"]),
                "error": "Choose one of your saved vehicles before creating a case.",
            },
        )

    complaint = complaint.strip()
    obd_code = obd_code.strip()
    if not complaint and not obd_code:
        return render_template(
            request,
            "case_new.html",
            {
                "vehicles": get_vehicles(current_user["id"]),
                "error": "Enter a customer complaint, an OBD-II code, or both.",
            },
        )

    result, _ = run_diagnostic_with_knowledge(
        obd_code=obd_code,
        symptom=complaint,
        vehicle=selected_vehicle,
    )
    suggested_parts, suggested_tools = split_case_parts_and_tools(result["parts"])
    saved_complaint = complaint or f"OBD-II code: {obd_code.upper()}"
    if complaint and obd_code:
        saved_complaint = f"{complaint} (OBD-II code: {obd_code.upper()})"

    case_id = add_customer_case(
        user_id=current_user["id"],
        vehicle_id=selected_vehicle["id"],
        customer_name=customer_name.strip(),
        customer_email=customer_email.strip(),
        customer_phone=customer_phone.strip(),
        complaint=saved_complaint,
        diagnosis_summary=result["summary"],
        severity=result["severity"],
        suggested_parts=suggested_parts,
        suggested_tools=suggested_tools,
        store_guidance=result["parts_store_notes"],
        follow_up_channel=follow_up_channel,
    )
    return RedirectResponse(f"/cases/{case_id}", status_code=303)


@app.get("/cases/{case_id}", response_class=HTMLResponse)
def case_detail_page(case_id: int, request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    customer_case = get_customer_case(case_id, current_user["id"])
    if not customer_case:
        return RedirectResponse("/cases", status_code=303)

    return render_template(
        request,
        "case_detail.html",
        {
            "customer_case": customer_case,
            "follow_up_statuses": FOLLOW_UP_STATUSES,
            "follow_up_drafts": build_follow_up_drafts(customer_case),
        },
    )


@app.get("/cases/{case_id}/report", response_class=HTMLResponse)
def case_report_page(case_id: int, request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    customer_case = get_customer_case(case_id, current_user["id"])
    if not customer_case:
        return RedirectResponse("/cases", status_code=303)

    return render_template(
        request,
        "case_report.html",
        {"customer_case": customer_case},
    )


@app.post("/cases/{case_id}/follow-up-status", response_class=HTMLResponse)
def update_case_follow_up_status(
    case_id: int,
    request: Request,
    status: str = Form(...),
):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    customer_case = get_customer_case(case_id, current_user["id"])
    if not customer_case:
        return RedirectResponse("/cases", status_code=303)

    if status not in FOLLOW_UP_STATUSES:
        return render_template(
            request,
            "case_detail.html",
            {
                "customer_case": customer_case,
                "follow_up_statuses": FOLLOW_UP_STATUSES,
                "follow_up_drafts": build_follow_up_drafts(customer_case),
                "error": "Choose a valid follow-up status.",
            },
        )

    update_customer_case_follow_up_status(
        case_id=case_id,
        user_id=current_user["id"],
        status=status,
    )
    return RedirectResponse(f"/cases/{case_id}", status_code=303)


@app.get("/knowledge-base", response_class=HTMLResponse)
def knowledge_base_page(request: Request):
    if not get_current_user(request):
        return redirect_to_login()

    return render_template(
        request,
        "knowledge_base.html",
        {"knowledge_items": get_knowledge_items()},
    )


@app.post("/knowledge-base", response_class=HTMLResponse)
def add_knowledge_base_item(
    request: Request,
    part_category: str = Form(...),
    problem: str = Form(...),
    symptom: str = Form(...),
    suggested_parts: str = Form(""),
    suggested_tools: str = Form(""),
    store_notes: str = Form(""),
    source_label: str = Form("Manual entry"),
):
    if not get_current_user(request):
        return redirect_to_login()

    add_knowledge_item(
        part_category=part_category.strip(),
        problem=problem.strip(),
        symptom=symptom.strip(),
        suggested_parts=suggested_parts.strip(),
        suggested_tools=suggested_tools.strip(),
        store_notes=store_notes.strip(),
        source_label=source_label.strip() or "Manual entry",
    )
    return render_template(
        request,
        "knowledge_base.html",
        {
            "knowledge_items": get_knowledge_items(),
            "message": "Knowledge item saved successfully.",
        },
    )


@app.get("/store-comparison", response_class=HTMLResponse)
def store_comparison_page(request: Request):
    if not get_current_user(request):
        return redirect_to_login()

    return render_template(
        request,
        "store_comparison.html",
        {"store_options": get_store_options()},
    )


@app.get("/vehicles", response_class=HTMLResponse)
def vehicles_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    return render_template(
        request,
        "vehicles.html",
        {"vehicles": get_vehicles(current_user["id"])},
    )


@app.post("/vehicles", response_class=HTMLResponse)
def add_vehicle_page(
    request: Request,
    year: int = Form(...),
    make: str = Form(...),
    model: str = Form(...),
    mileage: int = Form(...),
    engine: str = Form(""),
):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    add_vehicle(
        user_id=current_user["id"],
        year=year,
        make=make,
        model=model,
        mileage=mileage,
        engine=engine,
    )
    return render_template(
        request,
        "vehicles.html",
        {
            "vehicles": get_vehicles(current_user["id"]),
            "message": "Vehicle saved successfully.",
        },
    )


@app.get("/diagnose", response_class=HTMLResponse)
def diagnose_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    return render_template(
        request,
        "diagnose.html",
        {"vehicles": get_vehicles(current_user["id"]), "result": None},
    )


@app.get("/intake", response_class=HTMLResponse)
def guided_intake_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    return render_template(
        request,
        "intake.html",
        {
            "vehicles": get_vehicles(current_user["id"]),
            "result": None,
            "intake_values": {},
        },
    )


@app.post("/intake", response_class=HTMLResponse)
def submit_guided_intake(
    request: Request,
    vehicle_id: int = Form(...),
    obd_code: str = Form(""),
    symptom: str = Form(""),
    customer_name: str = Form(""),
    customer_email: str = Form(""),
    customer_phone: str = Form(""),
    follow_up_channel: str = Form("none"),
    save_as_case: bool = Form(False),
):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    vehicles = get_vehicles(current_user["id"])
    selected_vehicle = get_vehicle(vehicle_id, current_user["id"])
    intake_values = {
        "vehicle_id": vehicle_id,
        "obd_code": obd_code,
        "symptom": symptom,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "follow_up_channel": follow_up_channel,
        "save_as_case": save_as_case,
    }
    if not selected_vehicle:
        return render_template(
            request,
            "intake.html",
            {
                "vehicles": vehicles,
                "result": None,
                "intake_values": intake_values,
                "error": "Choose one of your saved vehicles before continuing.",
            },
        )

    obd_code = obd_code.strip()
    symptom = symptom.strip()
    if not obd_code and not symptom:
        return render_template(
            request,
            "intake.html",
            {
                "vehicles": vehicles,
                "result": None,
                "selected_vehicle": selected_vehicle,
                "intake_values": intake_values,
                "error": "Enter an OBD-II code, a customer complaint, or both.",
            },
        )

    result, input_text = run_diagnostic_with_knowledge(
        obd_code=obd_code,
        symptom=symptom,
        vehicle=selected_vehicle,
    )
    add_diagnostic_session(
        user_id=current_user["id"],
        vehicle_id=selected_vehicle["id"],
        input_text=input_text,
        summary=result["summary"],
        severity=result["severity"],
        causes=result["causes"],
        inspection=result["inspection"],
        parts=result["parts"],
        parts_store_notes=result["parts_store_notes"],
        safety=result["safety"],
    )

    created_case_id = None
    if save_as_case:
        suggested_parts, suggested_tools = split_case_parts_and_tools(result["parts"])
        saved_complaint = symptom or f"OBD-II code: {obd_code.upper()}"
        if symptom and obd_code:
            saved_complaint = f"{symptom} (OBD-II code: {obd_code.upper()})"
        created_case_id = add_customer_case(
            user_id=current_user["id"],
            vehicle_id=selected_vehicle["id"],
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip(),
            customer_phone=customer_phone.strip(),
            complaint=saved_complaint,
            diagnosis_summary=result["summary"],
            severity=result["severity"],
            suggested_parts=suggested_parts,
            suggested_tools=suggested_tools,
            store_guidance=result["parts_store_notes"],
            follow_up_channel=follow_up_channel,
        )

    return render_template(
        request,
        "intake.html",
        {
            "vehicles": vehicles,
            "result": result,
            "selected_vehicle": selected_vehicle,
            "input_text": input_text,
            "intake_values": intake_values,
            "created_case_id": created_case_id,
        },
    )


@app.post("/diagnose", response_class=HTMLResponse)
def run_diagnosis(
    request: Request,
    vehicle_id: int = Form(0),
    obd_code: str = Form(""),
    symptom: str = Form(""),
):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    selected_vehicle = (
        get_vehicle(vehicle_id, current_user["id"]) if vehicle_id > 0 else None
    )
    result, input_text = run_diagnostic_with_knowledge(
        obd_code=obd_code,
        symptom=symptom,
        vehicle=selected_vehicle,
    )

    add_diagnostic_session(
        user_id=current_user["id"],
        vehicle_id=vehicle_id if selected_vehicle else None,
        input_text=input_text,
        summary=result["summary"],
        severity=result["severity"],
        causes=result["causes"],
        inspection=result["inspection"],
        parts=result["parts"],
        parts_store_notes=result["parts_store_notes"],
        safety=result["safety"],
    )

    return render_template(
        request,
        "diagnose.html",
        {
            "vehicles": get_vehicles(current_user["id"]),
            "result": result,
            "input_text": input_text,
            "selected_vehicle": selected_vehicle,
        },
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    return render_template(
        request,
        "history.html",
        {"history": get_diagnostic_history(current_user["id"])},
    )


@app.post("/api/voice/diagnose")
def voice_diagnose(
    request_data: VoiceDiagnosticRequest,
    x_mechmate_voice_key: str | None = Header(default=None),
):
    if not is_voice_request_authorized(x_mechmate_voice_key):
        raise HTTPException(status_code=401, detail="Unauthorized voice tool request.")

    vehicle = build_voice_vehicle(request_data)
    result, _ = run_diagnostic_with_knowledge(
        obd_code=request_data.obd_code or "",
        symptom=request_data.symptom or "",
        vehicle=vehicle,
    )

    return {
        "spoken_response": build_spoken_response(result),
        "summary": result["summary"],
        "severity": result["severity"],
        "causes": result["causes"],
        "inspection": result["inspection"],
        "parts": result["parts"],
        "parts_store_notes": result["parts_store_notes"],
        "safety": result["safety"],
    }
