import hmac
import os

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
    add_diagnostic_session,
    add_knowledge_item,
    add_user,
    add_vehicle,
    get_diagnostic_history,
    get_knowledge_items,
    get_user_by_email,
    get_user_by_id,
    get_vehicle,
    get_vehicles,
    init_db,
    search_knowledge_items,
)
from app.diagnostic_engine import run_diagnostic


app = FastAPI(title="MechMate AI")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

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


def run_diagnostic_with_knowledge(
    obd_code: str,
    symptom: str,
    vehicle: dict | None,
):
    knowledge_item = None
    if not obd_code.strip() and symptom.strip():
        knowledge_matches = search_knowledge_items(symptom)
        knowledge_item = knowledge_matches[0] if knowledge_matches else None

    return run_diagnostic(
        obd_code=obd_code,
        symptom=symptom,
        vehicle=vehicle,
        knowledge_item=knowledge_item,
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render_template(request, "index.html")


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
