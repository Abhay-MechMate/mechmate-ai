# MechMate AI 5-Minute Demo Script

## Goal

Show the full local MVP journey: vehicle context, guided diagnosis, parts and
store planning, customer-case handoff, printable report, and future voice
readiness.

## Demo Flow

1. **Log in.** Open the local site and sign in with a demo account. Point out
   that vehicles, diagnostic history, and customer cases are scoped to the
   signed-in account.
2. **Add a vehicle.** Go to **Vehicles**. Enter a valid VIN and use **Decode
   VIN** to fill available details, or choose a year and use the NHTSA-backed
   make/model suggestions. Explain that a make or model can still be typed
   manually.
3. **Open Guided Intake.** Select the saved vehicle and show the live selected
   vehicle summary.
4. **Run an OBD-II diagnosis.** Enter `P0301` and submit. Highlight the
   summary, severity, possible causes, inspection steps, suggested parts/tools,
   parts-store guidance, and safety note.
5. **Run a no-code diagnosis.** Submit `my tire is deflating`. Point out that
   the editable Knowledge Base is checked before the generic local symptom
   fallback.
6. **Save a customer case.** Add optional customer details, choose a follow-up
   channel, check **Save this as a customer case**, and submit. Open the
   success link to the created case.
7. **Review the case.** Show the saved diagnostic snapshot, store guidance,
   follow-up status, and static follow-up drafts.
8. **Open the printable report.** Use **View printable report** and show print
   preview. The report includes the diagnostic disclaimer and store comparison
   factors.
9. **Show Store Comparison.** Explain that it is a local planning layer for
   cost, distance, shipping, warranty, and fitment—not live inventory or price
   data.
10. **Show the voice endpoint.** Open `/docs`, expand `POST
    /api/voice/diagnose`, and show its structured request and response. Do not
    claim that Syllable is connected.

## Talking Points

### What is built

- Local authentication with account-specific vehicles, history, and cases.
- NHTSA-backed vehicle suggestions and optional VIN autofill.
- OBD-II and no-code symptom diagnostics with a local, editable knowledge base.
- Suggested parts/tools, safety guidance, Store Comparison planning, customer
  cases, printable reports, and static follow-up drafts.

### What is AI-ready

The local rules and editable knowledge base provide structured inputs and
outputs for future AI assistance. Optional OpenAI diagnostics are backend-only
and disabled unless explicitly configured; this is not a trained AI model.

### What is Syllable-ready

`POST /api/voice/diagnose` accepts vehicle context and a code or symptom, then
returns a voice-ready summary plus the structured diagnostic result.

### What is not connected yet

- No live Syllable calls, messages, email, text, WhatsApp, or voice calls.
- No live parts inventory, pricing, distance, shipping, or store APIs.
- No public cloud deployment or public HTTPS endpoint.

### What comes next

Run the MVP on a persistent cloud host, configure server-only secrets and
HTTPS, choose durable database hosting, then connect Syllable to the protected
voice endpoint after end-to-end testing.
