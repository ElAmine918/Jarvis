import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jarvis.tools.admin_tool import AdminActionTool
from jarvis.core.approvals import PENDING_APPROVALS, APPROVAL_RESULTS


@pytest.fixture
def admin_tool():
    return AdminActionTool()


@pytest.mark.asyncio
async def test_admin_tool_unconfigured_telegram(admin_tool):
    with patch("jarvis.tools.admin_tool.TELEGRAM_BOT_TOKEN", ""), \
         patch("jarvis.tools.admin_tool.ALLOWED_TELEGRAM_USER_IDS", []):
        res = await admin_tool.execute(action="stop", container_name="test", reason="test")
        assert "❌ Impossible" in res


@pytest.mark.asyncio
async def test_admin_tool_unrecognized_action(admin_tool):
    with patch("jarvis.tools.admin_tool.TELEGRAM_BOT_TOKEN", "fake_token"), \
         patch("jarvis.tools.admin_tool.ALLOWED_TELEGRAM_USER_IDS", [123]):
        res = await admin_tool.execute(action="format_disk", container_name="test", reason="test")
        assert "🚫 Action Docker" in res
        assert "non reconnue" in res


@pytest.mark.asyncio
async def test_admin_tool_approval_and_execution(admin_tool):
    async def approve_on_post(*args, **kwargs):
        markup = kwargs.get("json", {}).get("reply_markup", {})
        btn_data = markup.get("inline_keyboard", [[{}]])[0][0].get("callback_data", "")
        if "_" in btn_data:
            req_id = btn_data.split("_", 1)[1]
            APPROVAL_RESULTS[req_id] = True
            if req_id in PENDING_APPROVALS:
                PENDING_APPROVALS[req_id].set()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        return mock_resp

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"container stopped", b"")

    with patch("jarvis.tools.admin_tool.TELEGRAM_BOT_TOKEN", "fake_token"), \
         patch("jarvis.tools.admin_tool.ALLOWED_TELEGRAM_USER_IDS", [123]), \
         patch("httpx.AsyncClient.post", side_effect=approve_on_post), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        res = await admin_tool.execute(action="stop", container_name="open-webui", reason="maintenance")
        assert "✅ L'administrateur a approuvé" in res
        assert "container stopped" in res
