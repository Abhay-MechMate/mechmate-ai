from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    add_user,
    add_vehicle,
    get_diagnostic_history,
    get_user_by_email,
    get_user_by_id,
    get_vehicle,
    get_vehicles,
    init_db,
)
from app.diagnostic_engine import run_diagnostic


app = FastAPI(title="MechMate AI")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Create database tables when the website starts.
init_db()


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


@app.get("/vehicles", response_class=HTMLResponse)
def vehicles_page(request: Request):
    return render_template(request, "vehicles.html", {"vehicles": get_vehicles()})


@app.post("/vehicles", response_class=HTMLResponse)
def add_vehicle_page(
    request: Request,
    year: int = Form(...),
    make: str = Form(...),
    model: str = Form(...),
    mileage: int = Form(...),
    engine: str = Form(""),
):
    add_vehicle(year=year, make=make, model=model, mileage=mileage, engine=engine)
    return render_template(
        request,
        "vehicles.html",
        {"vehicles": get_vehicles(), "message": "Vehicle saved successfully."},
    )


@app.get("/diagnose", response_class=HTMLResponse)
def diagnose_page(request: Request):
    return render_template(request, "diagnose.html", {"vehicles": get_vehicles(), "result": None})


@app.post("/diagnose", response_class=HTMLResponse)
def run_diagnosis(
    request: Request,
    vehicle_id: int = Form(0),
    obd_code: str = Form(""),
    symptom: str = Form(""),
):
    selected_vehicle = get_vehicle(vehicle_id) if vehicle_id > 0 else None
    result, input_text = run_diagnostic(obd_code=obd_code, symptom=symptom, vehicle=selected_vehicle)

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

    return render_template(
        request,
        "diagnose.html",
        {
            "vehicles": get_vehicles(),
            "result": result,
            "input_text": input_text,
            "selected_vehicle": selected_vehicle,
        },
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    return render_template(request, "history.html", {"history": get_diagnostic_history()})
