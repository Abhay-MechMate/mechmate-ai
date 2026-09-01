# MechMate AI Product Direction

## Current MVP

MechMate AI is an automotive diagnostic and parts-guidance website for car
owners and parts-store associates. A user saves vehicle context, enters an
OBD-II code or a customer complaint/symptom, and receives cautious local
guidance: likely causes, inspection steps, suggested parts or tools,
parts-store guidance, and safety notes. Local accounts keep vehicles and
diagnostic history account-specific.

The active diagnostic source is a small, rule-based, AI-ready diagnostic
knowledge base. It is not a trained AI model and does not make external AI
calls. Common no-code complaint entries are editable through the local
Knowledge Base page and are searched before the generic symptom fallback.

## Dad's Workflow Interpretation

The intended workflow is practical and conversational: begin with what the
customer says is wrong, capture the vehicle details and any scan code, narrow
the likely cause through inspection, and help identify the right parts or tools
without promising a repair before the cause is confirmed. The product should be
useful to both a car owner asking for a starting point and an associate helping
that customer ask better fitment and warranty questions.

## OBD-II Code Workflow

1. Select or save the vehicle profile.
2. Enter an OBD-II code, for example `P0301`.
3. MechMate returns the current local guidance for that code.
4. Review likely causes, inspection steps, suggested parts/tools, fitment
   reminders, and safety guidance.
5. Save the result in the signed-in user's diagnostic history.

## No-Code Symptom Workflow

1. Select or save the vehicle profile.
2. Describe the customer complaint / symptom when no scan code is available.
3. Examples include “my tire is deflating,” “smoking from exhaust,” and
   “battery keeps dying.”
4. MechMate returns the closest available symptom-based inspection path or a
   cautious generic starting point.
5. The user can return later with scan results or more detail.

## Parts-Store Guidance Workflow

The current MVP suggests part or tool categories and reminds the user to
inspect first and confirm year, make, model, mileage, and engine fitment before
buying. It does not claim exact parts or part numbers.

The current Store Comparison page is a local planning catalog. Future comparison
will help evaluate:

- Cost
- Distance to store
- Shipping
- Warranty
- Fitment confirmation

There is no live store inventory, pricing, distance, shipping estimate, or
parts-store API integration in the current MVP.

## Future Syllable Follow-Up Workflow

A future Syllable integration can collect the same vehicle and complaint data
through voice, then present or read the diagnostic response. Follow-up may later
continue through voice, chat, email, or text. The existing backend voice endpoint
is a foundation for this work, but no public agent configuration or external
deployment is complete.

## Future AI/OpenAI Workflow

Future backend-only AI work may use the vehicle profile, OBD-II code, symptom,
and diagnostic knowledge base to produce a validated structured response with
the same result fields used by the MVP. It must preserve cautious language,
validation, safety notes, and a rule-based fallback. No OpenAI calls, API keys,
model training claims, or browser-side provider calls are part of the current
implementation.

## Intentionally Not Built Yet

- Real parts-store inventory, pricing, distance, shipping, or warranty APIs
- Fake or real part numbers
- Live store comparison results
- Public Syllable agent configuration, HTTPS deployment, or external voice/chat
  follow-up
- Active OpenAI integration or a trained AI model
- Vehicle-specific repair certainty beyond the local prototype rules
