from unittest.mock import patch
import pytest
from jarvis.storage.memory import MemoryManager


@pytest.fixture
def mem(tmp_path):
    db_file = str(tmp_path / "memory_test.db")
    return MemoryManager(db_path=db_file)


@pytest.mark.asyncio
async def test_memory_skills_crud(mem):
    await mem.init_db()

    # Save
    res = await mem.save_skill(
        name="test_skill",
        description="A skill for testing",
        content="Do step 1 then step 2",
    )
    assert "sauvegardée avec succès" in res

    # Get
    skill = await mem.get_skill("test_skill")
    assert skill is not None
    assert skill["name"] == "test_skill"
    assert skill["description"] == "A skill for testing"
    assert skill["use_count"] == 1

    # Search with FTS5
    results = await mem.search_skills("testing")
    assert len(results) == 1
    assert results[0]["name"] == "test_skill"

    # Search all
    all_skills = await mem.search_skills("")
    assert len(all_skills) == 1


@pytest.mark.asyncio
async def test_memory_facts_crud(mem):
    await mem.init_db()

    # Save fact
    res = await mem.save_fact("owner_name", "Amine")
    assert "sauvegardé" in res

    # Get fact
    val = await mem.get_fact("owner_name")
    assert val == "Amine"

    # Non-existent fact
    missing = await mem.get_fact("unknown_key")
    assert missing is None

    # Update fact
    await mem.save_fact("owner_name", "Monsieur Amine")
    updated = await mem.get_fact("owner_name")
    assert updated == "Monsieur Amine"


@pytest.mark.asyncio
async def test_memory_error_paths(mem):
    # Pass an invalid db_path that causes sqlite connection to fail
    mem_bad = MemoryManager(db_path="/non_existent_dir_123/sub/bad.db")

    err_save_skill = await mem_bad.save_skill("s", "d", "c")
    assert "Erreur lors de la sauvegarde" in err_save_skill

    err_get_skill = await mem_bad.get_skill("s")
    assert err_get_skill is None

    err_search_skills = await mem_bad.search_skills("query")
    assert err_search_skills == []

    err_save_fact = await mem_bad.save_fact("k", "v")
    assert "Erreur lors de la sauvegarde" in err_save_fact

    err_get_fact = await mem_bad.get_fact("k")
    assert err_get_fact is None
