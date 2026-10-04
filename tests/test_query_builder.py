from jarvis.storage.query_builder import build_fts_query

def test_build_fts_query_basic():
    assert build_fts_query("Recette de tarte-aux-pommes !") == "Recette or tarte or aux or pommes"

def test_build_fts_query_quotes():
    assert build_fts_query('"Docker" et Proxmox') == "Docker or Proxmox"

def test_build_fts_query_stop_words_only():
    assert build_fts_query("et pour de la") == ""
