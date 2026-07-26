# MechMate AI

MechMate AI is a self-hosted FastAPI automotive diagnostic internship project.
It lets users save vehicle profiles, interpret a small mock OBD-II library,
record diagnostic sessions, review parts-store guidance, and expose the same
diagnostic flow through a voice-tool API.

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
- Future OpenAI, Syllable AI, and public homelab deployment work should keep
  API keys in environment variables and out of browser code.
