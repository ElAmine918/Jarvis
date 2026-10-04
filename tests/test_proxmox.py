import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.tools.proxmox_tool import (
    ProxmoxActionTool,
    ProxmoxStatusTool,
    get_proxmox_client,
)
from jarvis.core.approvals import APPROVAL_RESULTS, PENDING_APPROVALS


def test_get_proxmox_client_missing_token():
    with patch("jarvis.tools.proxmox_tool.PROXMOX_TOKEN_VALUE", ""):
        with pytest.raises(ValueError, match="PROXMOX_TOKEN_VALUE is not set"):
            get_proxmox_client()


def test_get_proxmox_client_success():
    with patch("jarvis.tools.proxmox_tool.PROXMOX_TOKEN_VALUE", "secret_val"):
        with patch("jarvis.tools.proxmox_tool.ProxmoxAPI") as mock_api:
            client = get_proxmox_client()
            mock_api.assert_called_once()
            assert client == mock_api.return_value


@pytest.mark.asyncio
async def test_proxmox_status_tool_success():
    tool = ProxmoxStatusTool()
    assert tool.name == "proxmox_status"
    assert "VMs" in tool.description
    assert tool.parameters == {"properties": {}, "required": []}

    mock_client = MagicMock()
    mock_node = MagicMock()
    mock_node.qemu.get.return_value = [{"vmid": "100", "name": "vm-test", "status": "running"}]
    mock_node.lxc.get.return_value = [{"vmid": "101", "name": "lxc-test", "status": "stopped"}]
    mock_client.nodes.return_value = mock_node

    with patch("jarvis.tools.proxmox_tool.get_proxmox_client", return_value=mock_client):
        res = await tool.execute()
        assert "[100] vm-test - Status: running" in res
        assert "[101] lxc-test - Status: stopped" in res


@pytest.mark.asyncio
async def test_proxmox_status_tool_exception():
    tool = ProxmoxStatusTool()
    with patch("jarvis.tools.proxmox_tool.get_proxmox_client", side_effect=RuntimeError("Proxmox down")):
        res = await tool.execute()
        assert "❌ Erreur lors de la récupération" in res
        assert "Proxmox down" in res


@pytest.mark.asyncio
async def test_proxmox_action_tool_missing_telegram():
    tool = ProxmoxActionTool()
    with patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", ""):
        res = await tool.execute(action="start", vmid="100", vm_type="qemu", reason="test")
        assert "❌ Impossible: Telegram n'est pas configuré" in res


@pytest.mark.asyncio
async def test_proxmox_action_tool_invalid_action():
    tool = ProxmoxActionTool()
    with (
        patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", "bot_token"),
        patch("jarvis.tools.proxmox_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
    ):
        res = await tool.execute(action="nuke_all", vmid="100", vm_type="qemu", reason="test")
        assert "🚫 Sécurité : action Proxmox 'nuke_all' non autorisée" in res


@pytest.mark.asyncio
async def test_proxmox_action_tool_invalid_vm_type():
    tool = ProxmoxActionTool()
    with (
        patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", "bot_token"),
        patch("jarvis.tools.proxmox_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
    ):
        res = await tool.execute(action="start", vmid="100", vm_type="openvz", reason="test")
        assert "🚫 Erreur : type 'openvz' inconnu" in res


@pytest.mark.asyncio
async def test_proxmox_action_tool_send_telegram_fails():
    tool = ProxmoxActionTool()
    with (
        patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", "bot_token"),
        patch("jarvis.tools.proxmox_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient.post", side_effect=RuntimeError("Network error")),
    ):
        res = await tool.execute(action="start", vmid="100", vm_type="qemu", reason="test")
        assert "❌ Erreur lors de l'envoi de la demande Telegram" in res


@pytest.mark.asyncio
async def test_proxmox_action_tool_timeout():
    tool = ProxmoxActionTool()
    with (
        patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", "bot_token"),
        patch("jarvis.tools.proxmox_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock),
        patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()),
    ):
        res = await tool.execute(action="start", vmid="100", vm_type="qemu", reason="test")
        assert "timeout de 5 minutes" in res


@pytest.mark.asyncio
async def test_proxmox_action_tool_rejected():
    tool = ProxmoxActionTool()

    async def fake_wait_for(coro, timeout):
        # Find the pending req_id and set rejected
        for req_id in list(PENDING_APPROVALS.keys()):
            APPROVAL_RESULTS[req_id] = False
        return True

    with (
        patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", "bot_token"),
        patch("jarvis.tools.proxmox_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock),
        patch("asyncio.wait_for", side_effect=fake_wait_for),
    ):
        res = await tool.execute(action="start", vmid="100", vm_type="qemu", reason="test")
        assert "❌ L'administrateur a REFUSÉ l'action" in res


@pytest.mark.asyncio
@pytest.mark.parametrize("action,vm_type", [
    ("start", "qemu"),
    ("stop", "lxc"),
    ("reboot", "qemu"),
    ("destroy", "lxc"),
])
async def test_proxmox_action_tool_approved_executions(action, vm_type):
    tool = ProxmoxActionTool()

    async def fake_wait_for(coro, timeout):
        for req_id in list(PENDING_APPROVALS.keys()):
            APPROVAL_RESULTS[req_id] = True
        return True

    mock_client = MagicMock()
    mock_node = MagicMock()
    mock_res = MagicMock()
    mock_node.qemu.return_value = mock_res
    mock_node.lxc.return_value = mock_res
    mock_client.nodes.return_value = mock_node

    with (
        patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", "bot_token"),
        patch("jarvis.tools.proxmox_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock),
        patch("asyncio.wait_for", side_effect=fake_wait_for),
        patch("jarvis.tools.proxmox_tool.get_proxmox_client", return_value=mock_client),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        res = await tool.execute(action=action, vmid="100", vm_type=vm_type, reason="routine test")
        assert "✅ L'administrateur a approuvé" in res
        if action == "start":
            mock_res.status.start.post.assert_called_once()
        elif action == "stop":
            mock_res.status.stop.post.assert_called_once()
        elif action == "reboot":
            mock_res.status.reboot.post.assert_called_once()
        elif action == "destroy":
            mock_res.delete.assert_called_once_with(purge=1)


@pytest.mark.asyncio
async def test_proxmox_action_tool_execution_error():
    tool = ProxmoxActionTool()

    async def fake_wait_for(coro, timeout):
        for req_id in list(PENDING_APPROVALS.keys()):
            APPROVAL_RESULTS[req_id] = True
        return True

    mock_client = MagicMock()
    mock_client.nodes.side_effect = RuntimeError("Proxmox API exploded")

    with (
        patch("jarvis.tools.proxmox_tool.TELEGRAM_BOT_TOKEN", "bot_token"),
        patch("jarvis.tools.proxmox_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock),
        patch("asyncio.wait_for", side_effect=fake_wait_for),
        patch("jarvis.tools.proxmox_tool.get_proxmox_client", return_value=mock_client),
    ):
        res = await tool.execute(action="start", vmid="100", vm_type="qemu", reason="test")
        assert "❌ Action approuvée mais erreur Proxmox" in res
