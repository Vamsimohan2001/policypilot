import os
import tempfile
from pathlib import Path

# Configure an isolated environment BEFORE any app module is imported.
_TMP = Path(tempfile.mkdtemp(prefix="policybot_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["CHROMA_DIR"] = str(_TMP / "chroma")
os.environ["POLICIES_DIR"] = str(Path(__file__).resolve().parent.parent / "policies")
os.environ["EMBEDDING_BACKEND"] = "local"
os.environ["OPENAI_API_KEY"] = ""
os.environ["LLM_ENABLED"] = "false"
os.environ["RATE_LIMIT_LOGIN_PER_MINUTE"] = "500"
os.environ["RATE_LIMIT_CHAT_PER_MINUTE"] = "500"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["AUTO_INGEST_ON_STARTUP"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
