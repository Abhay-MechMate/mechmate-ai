# Syllable Integration Plan

## Current Status

Syllable is **not connected yet**. MechMate currently exposes a local,
Syllable-ready FastAPI endpoint:

```text
POST /api/voice/diagnose
```

It accepts optional vehicle context and an OBD-II code and/or symptom. It uses
the existing diagnostic flow and returns a `spoken_response` plus structured
diagnostic guidance. It does not send email, text, WhatsApp, or voice messages.

## Local Testing

Start MechMate and open `http://127.0.0.1:8000/docs`. Expand `POST
/api/voice/diagnose`, select **Try it out**, and submit:

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

Example response shape:

```json
{
  "spoken_response": "...",
  "summary": "...",
  "severity": "...",
  "causes": ["..."],
  "inspection": ["..."],
  "parts": ["..."],
  "parts_store_notes": ["..."],
  "safety": "..."
}
```

When `VOICE_TOOL_API_KEY` is set, the caller must send:

```text
X-MechMate-Voice-Key: <VOICE_TOOL_API_KEY>
```

When the key is not configured, local requests work without that header.

## Future Syllable Tool Configuration

After public HTTPS deployment, configure Syllable to call:

- **URL:** `https://<mechmate-host>/api/voice/diagnose`
- **Method:** `POST`
- **Header:** `X-MechMate-Voice-Key: <VOICE_TOOL_API_KEY>`
- **Content type:** `application/json`

Tool parameters:

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `year` | integer | No | Vehicle model year. |
| `make` | string | No | Vehicle make. |
| `model` | string | No | Vehicle model. |
| `mileage` | integer | No | Current odometer reading. |
| `engine` | string | No | Engine or relevant vehicle notes. |
| `obd_code` | string | No | OBD-II diagnostic trouble code. |
| `symptom` | string | No | Customer complaint or symptom. |

## Agent Prompt Draft

> Collect the vehicle year, make, model, mileage, and engine details when the
> caller knows them. Ask for an OBD-II code and/or a clear customer complaint.
> Call the MechMate diagnostic tool with only the information the caller gave.
> Read the returned `spoken_response` naturally, emphasize any safety note,
> and present the result as first-pass diagnostic guidance—not a guaranteed
> repair. Do not invent part numbers, store prices, or appointment details.

## Security and Rollout

Syllable should not be connected until MechMate has a public HTTPS URL, a
server-side `VOICE_TOOL_API_KEY`, and end-to-end access-control testing. Never
place real API keys in this document, a Syllable prompt, browser code, or Git.
