import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jarvis.tools.web_reader import (
    WebReaderTool,
    NewsSearchTool,
    HTMLToTextParser,
    _is_safe_url,
    _is_private_ip,
)


def test_is_private_ip():
    assert _is_private_ip("127.0.0.1") is True
    assert _is_private_ip("::1") is True
    assert _is_private_ip("10.0.0.1") is True
    assert _is_private_ip("192.168.1.50") is True
    assert _is_private_ip("172.16.0.1") is True
    assert _is_private_ip("169.254.169.254") is True
    assert _is_private_ip("8.8.8.8") is False
    assert _is_private_ip("1.1.1.1") is False


def test_is_safe_url_ssrf_blocking():
    # Direct loopback and private IPs
    assert _is_safe_url("http://localhost:8080") is False
    assert _is_safe_url("http://127.0.0.1:8080") is False
    assert _is_safe_url("http://192.168.2.100") is False
    assert _is_safe_url("http://10.0.0.1/admin") is False
    assert _is_safe_url("http://169.254.169.254/latest/meta-data") is False

    # Blocked Docker service hostnames
    assert _is_safe_url("http://jarvis-pgvector:5432") is False
    assert _is_safe_url("http://docker-proxy:2375") is False
    assert _is_safe_url("http://chromium:3000") is False

    # Bad schemes
    assert _is_safe_url("file:///etc/passwd") is False
    assert _is_safe_url("ftp://ftp.server.com") is False
    assert _is_safe_url("gopher://server.com") is False
    assert _is_safe_url("") is False


def test_html_to_text_parser():
    parser = HTMLToTextParser()
    raw_html = "<html><head><title>Test</title><script>alert(1);</script></head><body><h1>Bonjour</h1><p>Contenu du paragraphe.</p></body></html>"
    parser.feed(raw_html)
    text = parser.get_text()
    assert "Bonjour" in text
    assert "Contenu du paragraphe." in text
    assert "alert" not in text


@pytest.mark.asyncio
async def test_web_reader_tool_ssrf_blocked():
    tool = WebReaderTool()
    res = await tool.execute(url="http://127.0.0.1:8080/secret")
    assert "🚫 URL bloquée" in res


@pytest.mark.asyncio
async def test_web_reader_tool_success():
    tool = WebReaderTool()
    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.text = "<html><body><h1>Page Publique</h1><p>Bienvenue sur le site.</p></body></html>"
    mock_resp.raise_for_status = MagicMock()

    with patch("jarvis.tools.web_reader._is_safe_url", return_value=True), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await tool.execute(url="https://example.com")
        assert "Page Publique" in res
        assert "Bienvenue" in res


@pytest.mark.asyncio
async def test_web_reader_tool_redirect_to_ssrf_blocked():
    tool = WebReaderTool()
    # First hop returns 302 redirect to internal IP
    mock_redirect = MagicMock()
    mock_redirect.is_redirect = True
    mock_redirect.headers = {"location": "http://169.254.169.254/latest/meta-data/"}

    with patch("httpx.AsyncClient.get", return_value=mock_redirect):
        res = await tool.execute(url="https://attacker-public-site.com/redirect")
        assert "🚫 URL bloquée" in res


@pytest.mark.asyncio
async def test_news_search_tool():
    tool = NewsSearchTool()
    mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Google News</title>
        <item>
          <title>Découverte spatiale majeure</title>
          <pubDate>Sun, 04 Oct 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """.encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.content = mock_rss
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await tool.execute(query="espace")
        assert "Découverte spatiale majeure" in res
