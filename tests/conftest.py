"""
Shared fixtures for the test suite.

The test DATABASE_URL env-var is set *before* any app module is imported so
that the engine, SessionLocal, and Base all point at the throwaway test DB.
"""

import os
import shutil

# ── point at a disposable test database BEFORE importing any app code ──
_TEST_DB = os.path.join(os.path.dirname(__file__), "test_certificates.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"

import pytest                               # noqa: E402
from fastapi.testclient import TestClient    # noqa: E402

from app.config import CERTIFICATES_DIR     # noqa: E402
from app.database import Base, engine        # noqa: E402
from app.main import app                     # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    """Create fresh tables before each test, tear them down afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

    if CERTIFICATES_DIR.exists():
        shutil.rmtree(CERTIFICATES_DIR, ignore_errors=True)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_payload():
    return {
        "title": "Certificate of Achievement",
        "event_name": "Advanced Python Workshop",
        "event_date": "2024-08-20",
        "issuer_name": "Prof. Alan Turing",
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Williams", "email": "bob@example.com"},
            {"name": "Charlie Brown", "email": "charlie@example.com"},
        ],
    }
