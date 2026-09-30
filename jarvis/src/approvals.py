import asyncio
from typing import Dict

# Stockage global pour les demandes d'approbation en attente
PENDING_APPROVALS: Dict[str, asyncio.Event] = {}
APPROVAL_RESULTS: Dict[str, bool] = {}
