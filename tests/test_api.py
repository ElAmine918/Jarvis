import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from jarvis.interfaces.api import app


@pytest.fixture
def client():
    # Setup mock agent in app.state
    mock_agent = AsyncMock()
    mock_agent.last_backend_used = "mock-model"

    async def mock_gen(*args, **kwargs):
        yield "Réponse test de l'agent"

    mock_agent.process_message = mock_gen
    app.state.agent = mock_agent

    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_models_without_key_dev_mode(client):
    # In dev mode (JARVIS_API_KEY empty), access is permitted
    with patch("jarvis.interfaces.api._API_KEY", ""):
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        model_ids = [m["id"] for m in data["data"]]
        assert "jarvis-auto" in model_ids
        assert "jarvis-gemini" in model_ids


def test_list_models_with_api_key_auth(client):
    # When JARVIS_API_KEY is set, 401 is returned on missing/bad key
    with patch("jarvis.interfaces.api._API_KEY", "secret_key_123"):
        # Without header
        res_no_auth = client.get("/v1/models")
        assert res_no_auth.status_code == 401

        # With wrong key
        res_bad_auth = client.get("/v1/models", headers={"Authorization": "Bearer wrong"})
        assert res_bad_auth.status_code == 401

        # With correct key
        res_good_auth = client.get("/v1/models", headers={"Authorization": "Bearer secret_key_123"})
        assert res_good_auth.status_code == 200


def test_chat_completions_empty_messages(client):
    with patch("jarvis.interfaces.api._API_KEY", ""):
        payload = {"model": "jarvis-auto", "messages": []}
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 400


def test_chat_completions_non_streaming(client):
    with patch("jarvis.interfaces.api._API_KEY", ""):
        payload = {
            "model": "jarvis-auto",
            "messages": [{"role": "user", "content": "Bonjour Jarvis"}],
            "stream": False,
        }
        with patch("jarvis.storage.logger_db.log_conversation"):
            response = client.post("/v1/chat/completions", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "chat.completion"
            assert "choices" in data
            assert data["choices"][0]["message"]["content"] == "Réponse test de l'agent"


def test_admin_dashboard_auth(client):
    with patch("jarvis.interfaces.cli_admin.ADMIN_PASSWORD", "test_admin_pass"):
        # Unauthenticated request
        res = client.get("/admin")
        assert res.status_code == 401

        # Correct Basic Auth
        res_auth = client.get("/admin", auth=("admin", "test_admin_pass"))
        assert res_auth.status_code == 200
        assert "JARVIS OS" in res_auth.text
