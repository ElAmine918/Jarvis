import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jarvis.tools.browser_tool import BrowserNavigateTool, HTMLToTextParser


def test_browser_parser():
    parser = HTMLToTextParser()
    parser.feed("<div><h2>Titre</h2><p>Texte rendu.</p><style>.css{}</style></div>")
    assert "Titre" in parser.get_text()
    assert "Texte rendu." in parser.get_text()


@pytest.mark.asyncio
async def test_browser_duckduckgo_fallback_for_search_query():
    tool = BrowserNavigateTool()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Résultats de recherche</h1><p>Doc Python 3.14</p></body></html>"

    with patch("jarvis.tools.browser_tool._is_safe_url", return_value=True), \
         patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        res = await tool.execute(url_or_search="documentation python")
        assert "Doc Python 3.14" in res
        # Verify DuckDuckGo query was built in request payload
        sent_payload = mock_post.call_args[1]["json"]
        assert "duckduckgo.com" in sent_payload["url"]


@pytest.mark.asyncio
async def test_browser_ssrf_block():
    tool = BrowserNavigateTool()
    res = await tool.execute(url_or_search="http://192.168.2.1/admin")
    assert "🚫 URL invalide" in res
