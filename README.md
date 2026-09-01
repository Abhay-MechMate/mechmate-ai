# MechMate AI

MechMate AI is a local automotive diagnostic and parts-guidance MVP for car
owners and parts-store associates. It guides a user from vehicle context and a
code or customer complaint to cautious diagnostic guidance, inspection steps,
suggested parts/tools, store-planning factors, and optional customer cases.

The MVP supports OBD-II codes, no-code symptom workflows, NHTSA vehicle lookup
and VIN autofill, an editable knowledge base, customer cases and reports, and a
Syllable-ready voice endpoint. The local rule-based and knowledge-base engine
is an AI-ready diagnostic knowledge base, not a trained AI model.

## Quickstart on Windows

From the repository root, rebuild the virtual environment if needed, install
the pinned dependencies, and start the local site:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. API documentation is available at
`http://127.0.0.1:8000/docs`.

## Run Tests

With the virtual environment active:

```powershell
python -m pytest
```

Tests use their own temporary SQLite database and mocked external responses.
They do not require OpenAI, Syllable, NHTSA internet access, store APIs, or the
local `data/mechmate.db` file.

## Optional OpenAI Diagnostics

The local diagnostic engine is the default and safe fallback. AI diagnostics
are attempted only when both `USE_AI_DIAGNOSTICS=true` and `OPENAI_API_KEY` are
available in the server environment. Missing keys, API failures, and invalid AI
responses all fall back to local diagnostic guidance.

Enable optional AI diagnostics for the current PowerShell session:

```powershell
$env:OPENAI_API_KEY = "paste-your-key-here"
$env:OPENAI_MODEL = "gpt-5"
$env:USE_AI_DIAGNOSTICS = "true"
```

Force local-only diagnostics:

```powershell
$env:USE_AI_DIAGNOSTICS = "false"
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
```

Never put a real key in templates, browser JavaScript, committed files, or
`.env.example`. A real `.env` remains ignored by Git.

## Docker Local Run

Docker Compose builds the app and mounts local `data/` into `/app/data` for
local SQLite persistence:

```powershell
docker compose up -d --build
docker compose logs -f
```

Stop the local container with:

```powershell
docker compose down
```

## Project Guides

- [5-minute demo script](docs/demo_script.md)
- [Deployment plan](docs/deployment_plan.md)
- [Production-readiness checklist](docs/production_checklist.md)
- [Syllable integration plan](docs/syllable_integration_plan.md)
- [Product direction](docs/product_direction.md)

## Current Boundaries

- NHTSA lookup/VIN decoding is public-data support; manual vehicle entry still
  works if it is unavailable.
- Store Comparison is a planning layer and does not provide live inventory,
  pricing, shipping, distance, or real part numbers.
- Syllable, email, text, WhatsApp, and voice-message delivery are not connected.
- The project is not currently deployed to a public host or homelab.
