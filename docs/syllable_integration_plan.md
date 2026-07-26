# Syllable AI Integration Plan

## Current Status

MechMate AI has a FastAPI voice-tool endpoint at `POST /api/voice/diagnose`.
It accepts optional vehicle fields (`year`, `make`, `model`, `mileage`, and
`engine`), plus an OBD-II code and/or a symptom. The response includes a
voice-ready `spoken_response` along with structured diagnostic fields:
`summary`, `severity`, `causes`, `inspection`, `parts`, `parts_store_notes`,
and `safety`.

## Local Testing

Start the MechMate server and open `http://127.0.0.1:8000/docs`. Expand
`POST /api/voice/diagnose`, choose **Try it out**, and submit a sample request:

```json
{
  "year": 2022,
  "make": "Toyota",
  "model": "Camry",
  "mileage": 42000,
  "engine": "2.5L I4",
  "obd_code": "P0301",
  "symptom": ""
}
```

When no voice API key is configured, local requests are allowed without a
header. When one is configured, include the required header in the docs UI.

## Planned Syllable Flow

1. The car owner speaks to Syllable.
2. Syllable collects vehicle details, an OBD-II code, and/or a symptom.
3. Syllable calls the MechMate backend endpoint.
4. MechMate returns the diagnosis, safety notes, and parts-store guidance.
5. Syllable reads `spoken_response` aloud and can offer follow-up questions.

## Planned Public Deployment

Deploy MechMate to a homelab or hosted server before connecting a public voice
agent. Add HTTPS and configure API-key protection before exposing the endpoint
outside the local network. Keep the key in server environment variables, never
in a Syllable prompt, browser code, or committed file.

## Future Syllable Tool Configuration

- Endpoint URL: `https://<mechmate-host>/api/voice/diagnose`
- Method: `POST`
- Request JSON: `year`, `make`, `model`, `mileage`, `engine`, `obd_code`, and `symptom`
- Custom header: `X-MechMate-Voice-Key: <VOICE_TOOL_API_KEY>`

Example agent prompt:

> Collect the vehicle year, make, model, mileage, engine details, OBD-II code,
> and symptom when available. Call the MechMate diagnostic tool, then clearly
> read its spoken response. Emphasize any safety warning and do not claim a
> diagnosis is certain.

All URL and header values above are placeholders. Do not place real API keys or
secrets in this document or in Syllable configuration text.
