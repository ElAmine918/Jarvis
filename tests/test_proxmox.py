import pytest
from jarvis.tools.proxmox_tool import ProxmoxActionTool, ProxmoxStatusTool

def test_proxmox_action_tool_parameters():
    tool = ProxmoxActionTool()
    params = tool.parameters
    assert "action" in params["properties"]
    assert "vmid" in params["properties"]
    assert "vm_type" in params["properties"]
    assert "reason" in params["properties"]

@pytest.mark.asyncio
async def test_proxmox_action_tool_allowed_actions():
    tool = ProxmoxActionTool()
    # Test invalid action rejection without telegram
    res = await tool.execute(action="invalid_action", vmid="101", vm_type="lxc", reason="test")
    # Even if telegram is not set or set, invalid action should not pass
    assert "non autorisée" in res or "Impossible" in res
