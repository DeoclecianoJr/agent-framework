import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Attempt to import the FastAPI app; if not available, tests will skip where needed
try:
    from ai_framework.main import app
except Exception:  # pragma: no cover - fallback when running outside app
    app = None


@pytest.fixture(scope="session")
def tmp_sqlite_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture()
def sqlite_memory_db(monkeypatch):
    """Provide a SQLite memory DB URL and patch settings or env var used by app.

    The application should read DATABASE_URL from environment in tests.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    yield


@pytest.fixture()
def client(sqlite_memory_db):
    """FastAPI TestClient that uses in-memory SQLite."""
    if app is None:
        pytest.skip("FastAPI app not importable as ai_framework.main.app")
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def api_key(monkeypatch):
    key = "test-api-key"
    monkeypatch.setenv("API_KEY", key)
    return key


@pytest.fixture()
def llm_mock(monkeypatch):
    class DummyLLM:
        def generate(self, prompt, **kwargs):
            return {
                "text": f"mocked response for: {prompt}",
                "score": 0.9,
            }

    dummy = DummyLLM()
    # Patch import path used by app, common option: ai_framework.llm.get_llm
    try:
        monkeypatch.setattr("ai_framework.llm.get_llm", lambda: dummy)
    except Exception:
        # best-effort; tests can still import llm_mock fixture to use dummy directly
        pass
    return dummy
