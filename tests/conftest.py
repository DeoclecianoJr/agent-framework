import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Attempt to import the FastAPI app; if not available, tests will skip where needed
try:
    from app.main import app
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


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from app.core.models import Base
    
    # Create in-memory SQLite database with StaticPool to share connection
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def sqlite_memory_db(test_db_engine):
    """Provide a SQLite memory DB session for testing.
    
    Returns a SQLAlchemy Session connected to an in-memory SQLite database.
    """
    from sqlalchemy.orm import sessionmaker
    from app.core.dependencies import init_db
    
    # Create session
    SessionLocal = sessionmaker(bind=test_db_engine)
    
    # Initialize the dependencies system with our test database
    init_db(SessionLocal)
    
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()


@pytest.fixture
def authenticated_client(sqlite_memory_db):
    """Create an authenticated test client with API key."""
    from app.main import app
    from app.core.dependencies import get_db
    from app.core.models import APIKey
    from app.core.security import generate_api_key, hash_api_key
    import uuid
    
    # Override dependency to use test database
    app.dependency_overrides[get_db] = lambda: sqlite_memory_db
    
    # Create API key in test database
    raw_key = generate_api_key()
    api_key = APIKey(
        id=str(uuid.uuid4()),
        name="test_key",
        key_hash=hash_api_key(raw_key),
        is_active=True
    )
    sqlite_memory_db.add(api_key)
    sqlite_memory_db.commit()
    
    # Create client with authentication header
    client = TestClient(app)
    client.headers.update({"X-API-Key": raw_key})
    
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    """FastAPI TestClient that uses in-memory SQLite."""
    if app is None:
        pytest.skip("FastAPI app not importable as app.main.app")
    
    from app.core.dependencies import get_db, init_db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.core.models import Base
    
    # Create in-memory test database with StaticPool to share connection
    test_engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestSessionLocal = sessionmaker(bind=test_engine)
    
    # Reset global SessionLocal to use test database (fixes middlewares)
    init_db(TestSessionLocal)
    
    # Override dependency to use test database
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    # Cleanup
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


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
