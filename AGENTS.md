# Repository Guidelines

## Project Structure & Architecture

MechMate AI is a beginner-built, self-hosted FastAPI website for an automotive diagnostic internship project. Preserve the FastAPI + Jinja2 + SQLite architecture; do not convert it to a mobile app, GitHub Pages site, React, Next.js, PostgreSQL, or another framework without explicit approval.

`app/main.py` owns FastAPI routes and template rendering. Keep database setup and queries in `app/database.py`, and keep mock diagnostic rules in `app/diagnostic_engine.py`. Templates live in `app/templates/`; CSS and browser JavaScript live in `app/static/`. `data/mechmate.db` stores local vehicle and diagnostic-session data and must not be committed.

## Development Commands

From the repository root, activate the existing virtual environment, install pinned dependencies, and run the local site:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` and manually check the home page, vehicle form, diagnosis result, and history page after UI or route changes. Run the command from the repository root so `data/mechmate.db` resolves correctly.

## Change Workflow

Before changing application code, inspect the relevant files and propose a short plan. Make small, focused changes that are easy to test; do not rewrite working features. Afterward, state exactly which files changed and the command or browser flow used to verify them.

The current diagnostic engine is intentionally a small mock library. Vehicle year, make, and model dropdowns and vehicle context are already supported. Future OpenAI integration must run through backend Python code only; never place API keys or provider calls in templates or browser JavaScript. Syllable AI voice support and Docker/homelab deployment are later phases.

## Coding and Testing

Use four-space Python indentation, `snake_case` for functions and variables, and `UPPER_SNAKE_CASE` for constants. Keep type hints on public database and diagnostic functions. Always use parameterized SQLite queries.

There is no test suite yet. Add tests under `tests/` using `pytest`, with names such as `tests/test_diagnostic_engine.py` and `test_unknown_code_returns_safe_guidance`. Use a temporary database in tests, never the real local database.

## Git and Data Safety

Use concise, imperative commits such as `Add SQLite database storage`. Keep commits focused; PRs should describe the user-facing impact, verification performed, related issue if any, and screenshots for visual changes. Never commit `.env`, `.venv/`, API keys, or `data/`. Back up `data/mechmate.db` before a pull or schema migration.
