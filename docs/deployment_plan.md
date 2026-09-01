# Deployment Plan

## Current State

MechMate AI is a local FastAPI + Jinja2 + SQLite MVP with Docker Compose
support. It is not currently deployed to a cloud host or homelab.

## Local Development

From the repository root on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`; API documentation is at
`http://127.0.0.1:8000/docs`.

## Docker Local Run Plan

Docker Compose builds the FastAPI image and mounts local `data/` into the
container so the SQLite file persists across local container rebuilds.

```powershell
docker compose up -d --build
docker compose logs -f
```

Stop it with:

```powershell
docker compose down
```

## Required Server Environment Variables

Set these only in the server environment or a non-committed local `.env` file:

| Variable | Purpose |
| --- | --- |
| `MECHMATE_SESSION_SECRET` | Stable, strong signing secret for auth sessions. |
| `OPENAI_API_KEY` | Optional backend-only OpenAI credential. |
| `OPENAI_MODEL` | Optional OpenAI model selection, such as `gpt-5`. |
| `USE_AI_DIAGNOSTICS` | Set to `true` only to enable optional AI diagnostics. |
| `VOICE_TOOL_API_KEY` | Shared secret for the future protected voice-tool request header. |

Secrets must remain server-side. They must not be placed in templates, browser
JavaScript, Syllable prompts, committed `.env` files, screenshots, or logs.

## Future Cloud Hosting Options

Later, run the existing Docker container on a general container host, virtual
private server, or managed application platform. Select a host that supports:

- a persistent volume or managed database;
- server environment variables/secrets;
- custom domain and HTTPS;
- container logs and backups.

This document intentionally does not select a provider, create an account, or
deploy the project.

## Database Persistence

SQLite works well for the local MVP and a single persistent volume. Some cloud
platforms use temporary or ephemeral filesystem storage, which can erase a
SQLite database during redeploys or restarts. Before public use, confirm that
the chosen host offers a durable mounted volume and backups. A managed database
such as PostgreSQL may be the safer next step for multi-instance hosting,
concurrent production traffic, and operational backups.

## Voice Endpoint and HTTPS

The future voice tool endpoint is:

```text
POST /api/voice/diagnose
```

Syllable integration should wait until MechMate is on a public HTTPS URL. At
that time, set `VOICE_TOOL_API_KEY` and require the matching
`X-MechMate-Voice-Key` request header. Public HTTPS is required so an external
voice provider can call the endpoint securely.

## Not Using a Homelab Yet

Docker support is present for local development, but MechMate is not currently
being run from a homelab. A hosted deployment remains a later, deliberate step.
