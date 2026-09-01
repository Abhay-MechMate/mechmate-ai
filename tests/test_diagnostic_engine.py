from app.diagnostic_engine import run_diagnostic


EXPECTED_FIELDS = {
    "summary",
    "severity",
    "causes",
    "inspection",
    "parts",
    "parts_store_notes",
    "safety",
}


def test_p0301_returns_structured_diagnosis():
    result, input_text = run_diagnostic(obd_code="P0301")

    assert input_text == "P0301"
    assert set(result) == EXPECTED_FIELDS
    assert result["severity"] == "Medium to High"
    assert "cylinder 1 misfire" in result["summary"].lower()


def test_unknown_code_returns_safe_guidance():
    result, input_text = run_diagnostic(obd_code="P9999")

    assert input_text == "P9999"
    assert result["severity"] == "Unknown"
    assert "not in the current local diagnostic database" in result["summary"]
    assert "do not continue driving" in result["safety"].lower()


def test_generic_unknown_symptom_falls_back_safely():
    result, input_text = run_diagnostic(symptom="random unknown symptom")

    assert input_text == "random unknown symptom"
    assert result["severity"] == "Unknown"
    assert "needs more information" in result["summary"].lower()
    assert result["parts_store_notes"]
