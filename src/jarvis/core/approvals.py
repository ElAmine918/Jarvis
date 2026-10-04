import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Stockage global pour compatibilité descendante
PENDING_APPROVALS: dict[str, asyncio.Event] = {}
APPROVAL_RESULTS: dict[str, bool] = {}


class ApprovalRequest:
    """Modèle d'une demande d'approbation administrateur."""

    def __init__(self, request_id: str, action: str, details: dict[str, Any], timeout: float = 300.0):
        self.request_id = request_id
        self.action = action
        self.details = details
        self.timeout = timeout
        self.created_at = time.time()
        self.event = asyncio.Event()
        self.result: Optional[bool] = None

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.timeout


class ApprovalManager:
    """Gestionnaire centralisé des approbations Human-in-the-Loop."""

    def __init__(self):
        self._requests: dict[str, ApprovalRequest] = {}

    def create_request(
        self, request_id: str, action: str, details: dict[str, Any], timeout: float = 300.0
    ) -> ApprovalRequest:
        req = ApprovalRequest(request_id, action, details, timeout)
        self._requests[request_id] = req
        PENDING_APPROVALS[request_id] = req.event
        return req

    async def wait_for_decision(self, request_id: str, timeout: Optional[float] = None) -> bool:
        req = self._requests.get(request_id)
        if not req:
            return False

        effective_timeout = timeout if timeout is not None else req.timeout
        try:
            await asyncio.wait_for(req.event.wait(), timeout=effective_timeout)
            return req.result is True
        except asyncio.TimeoutError:
            logger.warning(f"Timeout d'approbation pour la requête {request_id}")
            self.resolve_request(request_id, False)
            return False
        finally:
            self.cleanup(request_id)

    def resolve_request(self, request_id: str, approved: bool) -> bool:
        req = self._requests.get(request_id)
        if req:
            req.result = approved
            APPROVAL_RESULTS[request_id] = approved
            req.event.set()
            return True

        if request_id in PENDING_APPROVALS:
            APPROVAL_RESULTS[request_id] = approved
            PENDING_APPROVALS[request_id].set()
            return True

        return False

    def cleanup(self, request_id: str):
        self._requests.pop(request_id, None)
        PENDING_APPROVALS.pop(request_id, None)

    def get_pending_count(self) -> int:
        return len(self._requests)


# Instance globale
approval_manager = ApprovalManager()
