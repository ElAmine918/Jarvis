import asyncio

# Stockage global pour les demandes d'approbation en attente
PENDING_APPROVALS: dict[str, asyncio.Event] = {}
APPROVAL_RESULTS: dict[str, bool] = {}
