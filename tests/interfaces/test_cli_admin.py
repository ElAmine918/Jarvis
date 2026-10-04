import base64
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from jarvis.interfaces.api import app


client = TestClient(app)


def test_admin_dashboard_no_auth_dev_mode():
    with patch("jarvis.interfaces.cli_admin.ADMIN_PASSWORD", ""):
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert "JARVIS OS - Neural Command Center" in resp.text


def test_admin_dashboard_with_auth_unauthorized():
    with patch("jarvis.interfaces.cli_admin.ADMIN_PASSWORD", "secret_pass_123"):
        # Without credentials
        resp = client.get("/admin")
        assert resp.status_code == 401

        # With wrong credentials
        auth_header = "Basic " + base64.b64encode(b"admin:wrong_password").decode("ascii")
        resp_wrong = client.get("/admin", headers={"Authorization": auth_header})
        assert resp_wrong.status_code == 401


def test_admin_dashboard_with_auth_authorized():
    with patch("jarvis.interfaces.cli_admin.ADMIN_PASSWORD", "secret_pass_123"):
        auth_header = "Basic " + base64.b64encode(b"admin:secret_pass_123").decode("ascii")
        resp = client.get("/admin", headers={"Authorization": auth_header})
        assert resp.status_code == 200
        assert "JARVIS OS - Neural Command Center" in resp.text


def test_admin_api_data_payload():
    with patch("jarvis.interfaces.cli_admin.ADMIN_PASSWORD", ""), \
         patch("jarvis.interfaces.cli_admin.check_endpoint", AsyncMock(return_value=True)):
        resp = client.get("/admin/api/data")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools_count" in data
        assert isinstance(data["tools_count"], int)
        assert data["tools_count"] > 0
        assert "conversations" in data
        assert "actions" in data
        assert "backends" in data
        assert "stats" in data
        assert "cpu" in data["stats"]
        assert "ram" in data["stats"]
        assert data["backends"]["lm_studio"] is True
