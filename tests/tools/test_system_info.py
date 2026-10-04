import pytest
from jarvis.tools.system_info import SystemInfoTool


@pytest.fixture
def sys_info():
    return SystemInfoTool()


@pytest.mark.asyncio
async def test_system_info_cpu(sys_info):
    res = await sys_info.execute(query="cpu")
    assert "### CPU" in res
    assert "Utilisation globale" in res
    assert "Cœurs" in res


@pytest.mark.asyncio
async def test_system_info_memory(sys_info):
    res = await sys_info.execute(query="memory")
    assert "### Mémoire" in res
    assert "RAM" in res


@pytest.mark.asyncio
async def test_system_info_disk(sys_info):
    res = await sys_info.execute(query="disk")
    assert "### Disque" in res
    assert "Partition racine" in res


@pytest.mark.asyncio
async def test_system_info_processes(sys_info):
    res = await sys_info.execute(query="processes")
    assert "### Processus" in res


@pytest.mark.asyncio
async def test_system_info_all(sys_info):
    res = await sys_info.execute(query="all")
    assert "### CPU" in res
    assert "### Mémoire" in res
    assert "### Disque" in res


@pytest.mark.asyncio
async def test_system_info_unknown_query(sys_info):
    res = await sys_info.execute(query="invalid_query")
    assert "❌ Requête inconnue" in res
