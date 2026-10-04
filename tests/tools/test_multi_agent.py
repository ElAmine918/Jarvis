import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jarvis.tools.multi_agent import SubagentTool, AdvisorTool, FusionTool


@pytest.mark.asyncio
async def test_subagent_tool_success():
    tool = SubagentTool()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Calcul terminé: 42"}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await tool.execute(task="Calcule 6 * 7", model_tier="jarvis-gemini")
        assert "Réponse du sous-agent (jarvis-gemini)" in res
        assert "Calcul terminé: 42" in res


@pytest.mark.asyncio
async def test_advisor_tool_success():
    tool = AdvisorTool()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Conseil: privilégie la modularité."}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await tool.execute(question="Quelle architecture choisir ?", context="Projet agentique")
        assert "Avis du Conseiller" in res
        assert "privilégie la modularité" in res


@pytest.mark.asyncio
async def test_fusion_tool_success():
    tool = FusionTool()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Synthèse consensuelle des panélistes."}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await tool.execute(problem="Comment concevoir une base autonome ?")
        assert "Synthèse du Panel Fusion" in res
        assert "Synthèse consensuelle" in res
