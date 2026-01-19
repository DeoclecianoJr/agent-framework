import importlib
import os

from fastapi.testclient import TestClient


def test_scaffold_files_exist():
    assert os.path.exists("app/main.py")
    assert os.path.isdir("alembic")
    assert os.path.isdir("app/core")
    assert os.path.isdir("app/api")
    assert os.path.exists("requirements-dev.txt")


def test_import_app_main():
    module = importlib.import_module("app.main")
    assert hasattr(module, "app")


def test_health_endpoint_smoke():
    module = importlib.import_module("app.main")
    client = TestClient(module.app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("db") == "ok"
    assert data.get("llm") == "ok"
