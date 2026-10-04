import asyncio
import pytest
from jarvis.core.approvals import (
    ApprovalManager,
    ApprovalRequest,
    approval_manager,
    PENDING_APPROVALS,
    APPROVAL_RESULTS,
)


def test_approval_request_lifecycle():
    req = ApprovalRequest(
        request_id="req-123",
        action="stop",
        details={"container": "open-webui"},
        timeout=10.0,
    )
    assert req.request_id == "req-123"
    assert req.action == "stop"
    assert req.is_expired is False
    assert req.event.is_set() is False


@pytest.mark.asyncio
async def test_approval_manager_resolve_approved():
    mgr = ApprovalManager()
    req = mgr.create_request("req-abc", "restart", {"vmid": "100"}, timeout=5.0)

    assert "req-abc" in PENDING_APPROVALS

    async def approve_later():
        await asyncio.sleep(0.05)
        mgr.resolve_request("req-abc", True)

    asyncio.create_task(approve_later())
    decision = await mgr.wait_for_decision("req-abc")
    assert decision is True
    assert mgr.get_pending_count() == 0


@pytest.mark.asyncio
async def test_approval_manager_resolve_rejected():
    mgr = ApprovalManager()
    mgr.create_request("req-def", "destroy", {"vmid": "101"}, timeout=5.0)

    async def reject_later():
        await asyncio.sleep(0.05)
        mgr.resolve_request("req-def", False)

    asyncio.create_task(reject_later())
    decision = await mgr.wait_for_decision("req-def")
    assert decision is False


@pytest.mark.asyncio
async def test_approval_manager_timeout():
    mgr = ApprovalManager()
    mgr.create_request("req-timeout", "stop", {"container": "c1"}, timeout=0.1)
    decision = await mgr.wait_for_decision("req-timeout", timeout=0.1)
    assert decision is False
    assert mgr.get_pending_count() == 0


def test_backward_compatibility_dicts():
    req_id = "test_compat"
    ev = asyncio.Event()
    PENDING_APPROVALS[req_id] = ev

    # Emulate callback
    APPROVAL_RESULTS[req_id] = True
    PENDING_APPROVALS[req_id].set()

    assert ev.is_set() is True
    assert APPROVAL_RESULTS[req_id] is True

    PENDING_APPROVALS.pop(req_id, None)
    APPROVAL_RESULTS.pop(req_id, None)
