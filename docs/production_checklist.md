# Production-Readiness Checklist

- [ ] Set a strong, stable `MECHMATE_SESSION_SECRET` in the server environment.
- [ ] Set `VOICE_TOOL_API_KEY` before exposing the voice endpoint publicly.
- [ ] Configure optional OpenAI credentials only in the server environment.
- [ ] Confirm `.env` and all real secrets remain uncommitted.
- [ ] Decide whether persistent SQLite is sufficient or migrate to PostgreSQL.
- [ ] Add backups for any persistent database or mounted SQLite volume.
- [ ] Run `python -m pytest` before deployment.
- [ ] Verify login, logout, and account isolation with two accounts.
- [ ] Verify a user cannot access another account's customer case or report.
- [ ] Verify `POST /api/voice/diagnose` rejects requests without the correct
  `X-MechMate-Voice-Key` when `VOICE_TOOL_API_KEY` is configured.
- [ ] Verify NHTSA lookup or VIN-decoding failures leave manual vehicle entry
  available.
- [ ] Configure public HTTPS before connecting Syllable or other external tools.
- [ ] Verify logs do not contain API keys, voice keys, session secrets, or VINs.
