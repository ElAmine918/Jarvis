import re
import pytest

STOP_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "à", "a",
    "et", "ou", "mais", "donc", "or", "ni", "car", "pour", "dans", "en",
    "the", "and", "is", "it", "to", "of", "in", "on", "at", "with"
}

def build_fts_query(text: str) -> str:
    cleaned_text = re.sub(r'[^\w\s]', ' ', text)
    words = cleaned_text.split()
    filtered_words = [w for w in words if w.lower() not in STOP_WORDS]
    if not filtered_words:
        return ""
    return " or ".join(filtered_words)

def test_build_fts_query_basic():
    assert build_fts_query("Recette de tarte-aux-pommes !") == "Recette tarte aux pommes"

def test_build_fts_query_quotes():
    assert build_fts_query('"Docker" et Proxmox') == "Docker Proxmox"

def test_build_fts_query_stop_words_only():
    assert build_fts_query("et pour de la") == ""
