# MechMate AI

MechMate AI is a self-hosted automotive diagnostic and parts-guidance website
for car owners and parts-store associates. It helps users move from a vehicle
profile and a car concern to likely causes, inspection steps, suggested
parts/tools, safety guidance, and practical parts-store questions.

The current MVP supports both an OBD-II-code workflow and a no-code customer
complaint/symptom workflow. Its rule-based guidance is an AI-ready diagnostic
knowledge base, not a trained AI model.

Common no-code complaints can be maintained in the local Knowledge Base page.
The app searches those editable entries before using its generic symptom
fallback.

## Product Direction

- **Diagnostic assistant:** capture vehicle context and guide a cautious
  first-pass diagnosis.
- **OBD-II workflow:** enter a supported diagnostic trouble code for local
  causes, inspection steps, tools, and safety notes.
- **No-code symptom workflow:** describe a customer complaint such as a tire
  losing air, exhaust smoke, or a battery that keeps dying.
- **Parts/tools guidance:** identify useful part or tool categories and remind
  users to confirm fitment before purchase.
- **Store comparison MVP:** review a local planning catalog for cost, distance
  to store, shipping, warranty, and fitment confirmation without claiming live
  inventory or pricing today.
- **Syllable follow-up (planned):** support multimodal voice, chat, email, and
  text follow-up through a future integration.

See [docs/product_direction.md](docs/product_direction.md) for the detailed
MVP and future-work definition.

## Current Stack

- Python 3.12, FastAPI, and Jinja2
- SQLite at `data/mechmate.db`
- HTML, CSS, and JavaScript
- Docker Compose for future homelab deployment

## Run Locally

From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. The API documentation is available at
`http://127.0.0.1:8000/docs`.

## Optional AI Diagnostics

The local rule-based and knowledge-base diagnostic engine remains the default
and safe fallback. AI diagnostics are attempted only when both
`USE_AI_DIAGNOSTICS=true` and `OPENAI_API_KEY` are available in the server
environment. If the key is missing, the request fails, or the response is not
valid structured diagnostic data, MechMate uses the local engine instead.

To enable optional AI diagnostics for the current PowerShell session, set the
variables before starting Uvicorn:

```powershell
$env:OPENAI_API_KEY = "paste-your-key-here"
$env:OPENAI_MODEL = "gpt-5"
$env:USE_AI_DIAGNOSTICS = "true"
```

To force local fallback mode, use:

```powershell
$env:USE_AI_DIAGNOSTICS = "false"
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
```

Do not put a real key in templates, browser JavaScript, committed files, or
`.env.example`. `.env` remains ignored by Git.

## Run with Docker Compose

Install Docker Desktop or Docker Engine with the Compose plugin, then run from
the repository root:

```powershell
docker compose up -d --build
```

Open `http://127.0.0.1:8000`. Compose mounts the local `data/` directory at
`/app/data` in the container, so `data/mechmate.db` survives container restarts
and image rebuilds.

Stop the service:

```powershell
docker compose down
```

View service logs:

```powershell
docker compose logs -f
```

## Notes

- `data/` and real `.env` files are ignored by Git.
- The current diagnostic engine is rule-based and remains the active source of
  results.
- Store comparison does not use real inventory, pricing, part numbers, or
  parts-store APIs yet.
- Optional OpenAI diagnostics use backend environment variables only; Syllable
  and public deployment work remain separate future phases.
