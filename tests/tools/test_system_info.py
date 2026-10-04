from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.tools.system_info import SystemInfoTool, _run_command


@pytest.fixture
def sys_info():
    return SystemInfoTool()


def test_system_info_properties(sys_info):
    assert sys_info.name == "system_info"
    assert "cpu" in sys_info.description
    assert "query" in sys_info.parameters["properties"]


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
async def test_system_info_containers_with_and_without_docker(sys_info):
    with (
        patch("shutil.which", return_value="/usr/bin/docker"),
        patch("jarvis.tools.system_info._run_command", new_callable=AsyncMock) as mock_cmd,
    ):
        mock_cmd.return_value = "jarvis-container Up"
        res = await sys_info.execute(query="containers")
        assert "### Conteneurs Docker" in res
        assert "jarvis-container Up" in res

    with patch("shutil.which", return_value=None):
        res_no = await sys_info.execute(query="containers")
        assert "non présent" in res_no


@pytest.mark.asyncio
async def test_system_info_network_ports(sys_info):
    res = await sys_info.execute(query="network_ports")
    assert "### Ports en écoute" in res


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


@pytest.mark.asyncio
async def test_run_command_success_and_error():
    out = await _run_command("echo", "test_out")
    assert "test_out" in out

    out_err = await _run_command("non_existent_binary_12345")
    assert "Erreur" in out_err
