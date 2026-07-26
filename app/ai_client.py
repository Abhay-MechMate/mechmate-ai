"""Future backend adapter for OpenAI-powered diagnostic responses.

This module intentionally does not import the OpenAI SDK, read API keys, or make
network calls yet. The current rule-based diagnostic engine remains active.
"""


def format_vehicle_prompt_context(vehicle: dict | None) -> str:
    if not vehicle:
        return "No vehicle was selected."

    year = vehicle.get("year", "not provided")
    make = vehicle.get("make", "not provided")
    model = vehicle.get("model", "not provided")
    mileage = vehicle.get("mileage", "not provided")
    engine = vehicle.get("engine") or "not provided"

    return (
        f"Year: {year}\n"
        f"Make: {make}\n"
        f"Model: {model}\n"
        f"Mileage: {mileage}\n"
        f"Engine / notes: {engine}"
    )


def build_diagnostic_prompt(
    vehicle: dict | None,
    obd_code: str = "",
    symptom: str = "",
) -> str:
    """Build the future backend prompt without sending it anywhere."""
    obd_code = obd_code.strip().upper()
    symptom = symptom.strip()

    code_context = obd_code or "No OBD-II code provided"
    symptom_context = symptom or "No symptom provided"

    return f"""You are an automotive diagnostic assistant for MechMate AI.
Provide cautious, practical guidance and do not claim certainty without evidence.

Vehicle context:
{format_vehicle_prompt_context(vehicle)}

OBD-II code: {code_context}
Symptom: {symptom_context}

Return only a structured JSON object with these fields:
- summary: string
- severity: string
- causes: array of strings
- inspection: array of strings
- parts: array of strings
- safety: string
"""


def generate_ai_diagnosis(
    vehicle: dict | None,
    obd_code: str = "",
    symptom: str = "",
):
    """Placeholder for a future OpenAI backend request.

    The prompt is built now so its input/output contract can be reviewed, but no
    API key is read and no network request is made. Returning ``None`` keeps the
    current mock diagnostic engine as the only active diagnosis source.
    """
    build_diagnostic_prompt(vehicle, obd_code, symptom)
    return None
