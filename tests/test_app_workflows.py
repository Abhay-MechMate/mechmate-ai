from app.diagnostic_engine import OBD_DATABASE


VOICE_RESPONSE_FIELDS = {
    "spoken_response",
    "summary",
    "severity",
    "causes",
    "inspection",
    "parts",
    "parts_store_notes",
    "safety",
}


def signup(client, email: str, password: str = "safe-password"):
    response = client.post(
        "/signup",
        data={
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response


def add_vehicle(client, email: str, model: str):
    response = client.post(
        "/vehicles",
        data={
            "year": 2022,
            "make": "Toyota",
            "model": model,
            "mileage": 42000,
            "engine": "2.5L I4",
        },
    )
    assert response.status_code == 200

    from app.database import get_user_by_email, get_vehicles

    user = get_user_by_email(email)
    return get_vehicles(user["id"])[0]


def test_public_pages_and_protected_route_redirects(client):
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/signup").status_code == 200

    for path in ("/vehicles", "/diagnose", "/history"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"


def test_signup_login_and_logout(client):
    signup(client, "login-test@example.com")

    from app.database import get_user_by_email

    assert get_user_by_email("login-test@example.com") is not None

    logout_response = client.get("/logout", follow_redirects=False)
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/"

    protected_response = client.get("/vehicles", follow_redirects=False)
    assert protected_response.status_code == 303
    assert protected_response.headers["location"] == "/login"

    login_response = client.post(
        "/login",
        data={"email": "login-test@example.com", "password": "safe-password"},
        follow_redirects=False,
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/"


def test_vehicle_form_supports_suggested_and_custom_make_model_entries(client):
    signup(client, "vehicle-inputs@example.com")

    vehicle_page = client.get("/vehicles")
    assert vehicle_page.status_code == 200
    assert 'name="make"' in vehicle_page.text
    assert 'list="vehicleMakeOptions"' in vehicle_page.text
    assert 'name="model"' in vehicle_page.text
    assert 'list="vehicleModelOptions"' in vehicle_page.text
    assert 'name="vin"' in vehicle_page.text
    assert "Decode VIN" in vehicle_page.text
    assert "Not listed? Type manually." in vehicle_page.text

    custom_vehicle = client.post(
        "/vehicles",
        data={
            "year": 2024,
            "make": "Custom Motors",
            "model": "Prototype X",
            "mileage": 1200,
            "engine": "Electric prototype",
        },
    )
    assert custom_vehicle.status_code == 200
    assert "2024 Custom Motors Prototype X" in custom_vehicle.text

    vehicle_suggestions = client.get("/static/vehicle_dropdowns.js")
    assert vehicle_suggestions.status_code == 200
    assert "/api/vehicles/makes" in vehicle_suggestions.text
    assert "/api/vehicles/models" in vehicle_suggestions.text
    assert "/api/vehicles/decode-vin" in vehicle_suggestions.text


def test_knowledge_base_symptoms_are_used_before_generic_fallback(client):
    from app.main import run_diagnostic_with_knowledge

    tire_result, _ = run_diagnostic_with_knowledge(
        obd_code="",
        symptom="my tire is deflating",
        vehicle=None,
    )
    smoke_result, _ = run_diagnostic_with_knowledge(
        obd_code="",
        symptom="smoking from exhaust",
        vehicle=None,
    )

    assert "knowledge-base match" in tire_result["summary"].lower()
    assert tire_result["severity"] == "Needs Inspection"
    assert "knowledge-base match" in smoke_result["summary"].lower()
    assert "PCV valve" in smoke_result["summary"]


def test_openai_disabled_uses_local_fallback(client, monkeypatch):
    from app import ai_client
    from app.main import run_diagnostic_with_knowledge

    monkeypatch.setenv("USE_AI_DIAGNOSTICS", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "not-used-in-tests")
    monkeypatch.setattr(
        ai_client,
        "OpenAI",
        lambda: (_ for _ in ()).throw(AssertionError("OpenAI must not be called")),
    )

    result, _ = run_diagnostic_with_knowledge(
        obd_code="P0301",
        symptom="",
        vehicle=None,
    )

    assert result["summary"].startswith(OBD_DATABASE["P0301"]["summary"])


def test_missing_openai_key_uses_local_fallback(client, monkeypatch):
    from app.main import run_diagnostic_with_knowledge

    monkeypatch.setenv("USE_AI_DIAGNOSTICS", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result, _ = run_diagnostic_with_knowledge(
        obd_code="P0301",
        symptom="",
        vehicle=None,
    )

    assert result["summary"].startswith(OBD_DATABASE["P0301"]["summary"])


def test_voice_diagnose_works_without_login(client):
    response = client.post(
        "/api/voice/diagnose",
        json={"obd_code": "P0301", "symptom": ""},
    )

    assert response.status_code == 200
    assert VOICE_RESPONSE_FIELDS <= set(response.json())


def test_nhtsa_vehicle_lookup_routes_use_mocked_server_side_data(client, monkeypatch):
    from app import main

    main.NHTSA_MAKES_CACHE.clear()
    main.NHTSA_MODELS_CACHE.clear()
    requested_paths = []

    def fake_nhtsa_fetch(path: str):
        requested_paths.append(path)
        if path == "GetMakesForVehicleType/car":
            return {"Results": [{"MakeName": "Toyota"}, {"MakeName": "Honda"}]}
        if path == "GetModelsForMakeYear/make/Toyota/modelyear/2023":
            return {"Results": [{"Model_Name": "GR86"}, {"Model_Name": "Camry"}]}
        if path == "DecodeVinValuesExtended/1HGCM82633A004352":
            return {
                "Results": [
                    {
                        "ModelYear": "2018",
                        "Make": "HONDA",
                        "Model": "Civic",
                        "DisplacementL": "2",
                        "EngineCylinders": "4",
                        "EngineModel": "K20",
                        "FuelTypePrimary": "Gasoline",
                        "ErrorCode": "0",
                        "ErrorText": "0 - VIN decoded clean.",
                    }
                ]
            }
        raise AssertionError(f"Unexpected NHTSA request: {path}")

    monkeypatch.setattr(main, "fetch_nhtsa_json", fake_nhtsa_fetch)

    makes_response = client.get("/api/vehicles/makes?year=2023")
    assert makes_response.status_code == 200
    assert makes_response.json() == {"makes": ["Honda", "Toyota"]}
    assert client.get("/api/vehicles/makes?year=2023").json() == {
        "makes": ["Honda", "Toyota"]
    }
    assert requested_paths.count("GetMakesForVehicleType/car") == 1

    models_response = client.get("/api/vehicles/models?year=2023&make=Toyota")
    assert models_response.status_code == 200
    assert models_response.json() == {"models": ["Camry", "GR86"]}
    assert client.get("/api/vehicles/models?year=2023&make=Toyota").json() == {
        "models": ["Camry", "GR86"]
    }
    assert requested_paths.count("GetModelsForMakeYear/make/Toyota/modelyear/2023") == 1

    vin_response = client.get("/api/vehicles/decode-vin?vin=1HGCM82633A004352")
    assert vin_response.status_code == 200
    assert vin_response.json() == {
        "vehicle": {
            "year": 2018,
            "make": "HONDA",
            "model": "Civic",
            "engine": "2L, 4 cylinders, K20, Gasoline",
        },
        "error": None,
    }


def test_nhtsa_lookup_failure_and_invalid_vin_keep_manual_entry_available(client, monkeypatch):
    from app import main

    main.NHTSA_MAKES_CACHE.clear()
    main.NHTSA_MODELS_CACHE.clear()
    monkeypatch.setattr(main, "fetch_nhtsa_json", lambda path: None)

    makes_response = client.get("/api/vehicles/makes?year=2023")
    assert makes_response.status_code == 200
    assert makes_response.json()["makes"] == []
    assert "Type a make manually" in makes_response.json()["error"]

    models_response = client.get("/api/vehicles/models?year=2023&make=Toyota")
    assert models_response.status_code == 200
    assert models_response.json()["models"] == []
    assert "Type a model manually" in models_response.json()["error"]

    invalid_vin_response = client.get("/api/vehicles/decode-vin?vin=not-a-vin")
    assert invalid_vin_response.status_code == 200
    assert invalid_vin_response.json()["vehicle"] is None
    assert "17-character VIN" in invalid_vin_response.json()["error"]


def test_account_data_is_isolated_for_vehicles_history_and_cases(client):
    signup(client, "account-a@example.com")
    vehicle_a = add_vehicle(client, "account-a@example.com", "Account A Model")

    diagnosis_response = client.post(
        "/diagnose",
        data={"vehicle_id": vehicle_a["id"], "obd_code": "P0301", "symptom": ""},
    )
    assert diagnosis_response.status_code == 200

    case_response = client.post(
        "/cases/new",
        data={
            "vehicle_id": vehicle_a["id"],
            "customer_name": "Account A Customer",
            "customer_email": "customer-a@example.com",
            "customer_phone": "555-0100",
            "complaint": "my tire is deflating",
            "obd_code": "",
            "follow_up_channel": "text",
        },
        follow_redirects=False,
    )
    assert case_response.status_code == 303
    case_url = case_response.headers["location"]

    case_detail_a = client.get(case_url)
    assert case_detail_a.status_code == 200
    assert "Account A Customer" in case_detail_a.text

    status_response = client.post(
        f"{case_url}/follow-up-status",
        data={"status": "contacted"},
        follow_redirects=False,
    )
    assert status_response.status_code == 303
    assert "contacted" in client.get(case_url).text

    client.get("/logout")
    signup(client, "account-b@example.com")
    add_vehicle(client, "account-b@example.com", "Account B Model")

    vehicles_page = client.get("/vehicles")
    history_page = client.get("/history")
    cases_page = client.get("/cases")
    case_detail = client.get(case_url, follow_redirects=False)

    assert "Account A Model" not in vehicles_page.text
    assert "P0301" not in history_page.text
    assert "Account A Customer" not in cases_page.text
    assert case_detail.status_code == 303
    assert case_detail.headers["location"] == "/cases"


def test_case_reports_are_complete_and_private(client):
    signup(client, "report-owner@example.com")
    vehicle = add_vehicle(client, "report-owner@example.com", "Report Owner Model")

    case_response = client.post(
        "/cases/new",
        data={
            "vehicle_id": vehicle["id"],
            "customer_name": "Report Customer",
            "customer_email": "report-customer@example.com",
            "customer_phone": "555-0111",
            "complaint": "my tire is deflating",
            "obd_code": "",
            "follow_up_channel": "text",
        },
        follow_redirects=False,
    )
    assert case_response.status_code == 303
    case_url = case_response.headers["location"]
    report_url = f"{case_url}/report"

    case_detail = client.get(case_url)
    assert case_detail.status_code == 200
    assert "View printable report" in case_detail.text
    for draft_type in (
        "Text message",
        "Email",
        "Voice/phone script",
        "Syllable agent script",
    ):
        assert draft_type in case_detail.text
    assert (
        "These are draft messages only. No email, text, WhatsApp, or voice call is sent in this MVP."
        in case_detail.text
    )

    report_response = client.get(report_url)
    assert report_response.status_code == 200
    for expected_content in (
        "Report Customer",
        "Report Owner Model",
        "my tire is deflating",
        "Knowledge-base match",
        "Tire repair kit",
        "Tire pressure gauge",
        "This report is diagnostic guidance, not a guaranteed repair. Confirm fitment and inspect before replacing parts.",
    ):
        assert expected_content in report_response.text

    client.get("/logout")
    signup(client, "report-other@example.com")
    other_user_report = client.get(report_url, follow_redirects=False)
    assert other_user_report.status_code == 303
    assert other_user_report.headers["location"] == "/cases"


def test_dashboard_and_demo_seed_are_account_scoped(client):
    public_dashboard = client.get("/")
    assert public_dashboard.status_code == 200
    assert "Create an account" in public_dashboard.text

    unauthenticated_seed = client.post("/demo/seed", follow_redirects=False)
    assert unauthenticated_seed.status_code == 303
    assert unauthenticated_seed.headers["location"] == "/login"

    signup(client, "dashboard-a@example.com")
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    for expected_content in (
        "MVP overview",
        "Saved vehicle profiles",
        "Load demo data",
        "Local diagnostic engine:",
        "Syllable endpoint:",
    ):
        assert expected_content in dashboard.text

    first_seed = client.post("/demo/seed", follow_redirects=False)
    assert first_seed.status_code == 303
    assert first_seed.headers["location"] == "/?demo=loaded"

    seeded_dashboard = client.get(first_seed.headers["location"])
    assert "Demo data loaded for this account." in seeded_dashboard.text
    for expected_content in (
        "2021 Honda Civic",
        "Demo data: P0301 cylinder one misfire",
        "Demo Customer",
        "ready for follow-up",
    ):
        assert expected_content in seeded_dashboard.text

    from app.database import get_dashboard_stats, get_user_by_email

    account_a = get_user_by_email("dashboard-a@example.com")
    first_stats = get_dashboard_stats(account_a["id"])
    assert first_stats["total_vehicles"] == 1
    assert first_stats["total_diagnostic_sessions"] == 1
    assert first_stats["total_customer_cases"] == 1
    assert first_stats["cases_ready_for_follow_up"] == 1

    second_seed = client.post("/demo/seed", follow_redirects=False)
    assert second_seed.status_code == 303
    assert get_dashboard_stats(account_a["id"]) == first_stats

    client.get("/logout")
    signup(client, "dashboard-b@example.com")
    account_b_dashboard = client.get("/")
    assert "2021 Honda Civic" not in account_b_dashboard.text
    assert "Demo data: P0301 cylinder one misfire" not in account_b_dashboard.text
    assert "Demo Customer" not in account_b_dashboard.text

    account_b = get_user_by_email("dashboard-b@example.com")
    account_b_stats = get_dashboard_stats(account_b["id"])
    assert account_b_stats["total_vehicles"] == 0
    assert account_b_stats["total_diagnostic_sessions"] == 0
    assert account_b_stats["total_customer_cases"] == 0
