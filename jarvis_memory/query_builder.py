
import re
import pytest

STOP_WORDS = {"le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "à", "a", "et", "ou", "mais", "donc", "or", "ni", "car", "pour", "dans", "en"}

def build_fts_query(text: str) -> str:
    cleaned = re.sub(r'[^\w\s]', ' ', text)
    words = cleaned.split()
    filtered = [w for w in words if w.lower() not in STOP_WORDS]
    if not filtered: return ""
    return " or ".join(filtered)

def test_build_fts_query_basic():
    assert build_fts_query("Recette de tarte-aux-pommes !") == "Recette tarte aux pommes"
