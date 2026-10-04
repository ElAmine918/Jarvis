import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jarvis.tools.rag_tool import DocumentRAGTool


@pytest.fixture
def rag():
    return DocumentRAGTool()


@pytest.mark.asyncio
async def test_rag_forbidden_path(rag):
    res = await rag.execute(file_path="/etc/shadow", question="Quels sont les mots de passe ?")
    assert "🚫 Sécurité" in res


@pytest.mark.asyncio
async def test_rag_non_existent_file(rag, tmp_path):
    missing_file = str(tmp_path / "not_found.txt")
    res = await rag.execute(file_path=missing_file, question="Contenu ?")
    assert "n'existe pas" in res


@pytest.mark.asyncio
async def test_rag_successful_analysis(rag, tmp_path):
    doc = tmp_path / "doc.txt"
    doc.write_text("Le projet Jarvis utilise PostgreSQL et Ollama pour son infrastructure locale.", encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Jarvis utilise PostgreSQL et Ollama."}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        res = await rag.execute(file_path=str(doc), question="Quels outils sont utilisés ?")
        assert "Résultat de la recherche RAG sur doc.txt" in res
        assert "PostgreSQL et Ollama" in res
        assert mock_post.called
