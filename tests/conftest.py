import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create an app client backed by an isolated temporary SQLite database."""
    monkeypatch.setenv("USE_AI_DIAGNOSTICS", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("VOICE_TOOL_API_KEY", raising=False)

    from app import database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "mechmate_test.db")

    if "app.main" in sys.modules:
        main = importlib.reload(sys.modules["app.main"])
    else:
        main = importlib.import_module("app.main")

    database.init_db()

    with TestClient(main.app) as test_client:
        yield test_client
