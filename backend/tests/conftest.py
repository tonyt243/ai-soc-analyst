import pytest
from fastapi.testclient import TestClient

from app.alerts import store
from app.main import app


@pytest.fixture(autouse=True)
def _reset_alert_store():
    """The alert store is a module-level dict — clear it before every test
    so tests can't see alerts created by other tests."""
    store.reset()
    yield
    store.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
