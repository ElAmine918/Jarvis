import pytest
from unittest.mock import patch
from jarvis.tools.deep_research import DeepResearchTool


@pytest.mark.asyncio
async def test_deep_research_execute_triggers_task():
    tool = DeepResearchTool()
    assert tool.name == "call_deep_research"
    assert "topic" in tool.parameters["required"]

    with patch("asyncio.create_task") as mock_create_task:
        res = await tool.execute(topic="Quantum Computing in 2026")
        assert "✅" in res
        assert "Quantum Computing in 2026" in res
        assert mock_create_task.called


@pytest.mark.asyncio
async def test_deep_research_missing_topic():
    tool = DeepResearchTool()
    res = await tool.execute(topic="")
    assert "Erreur" in res
