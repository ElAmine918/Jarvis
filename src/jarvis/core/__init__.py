"""Module core de Jarvis : orchestration, agent principal, routage et approbations."""

__all__ = ["JarvisAgent", "get_all_backends", "PENDING_APPROVALS", "APPROVAL_RESULTS"]


def __getattr__(name: str):
    if name == "JarvisAgent":
        from jarvis.core.agent import JarvisAgent
        return JarvisAgent
    if name in ("PENDING_APPROVALS", "APPROVAL_RESULTS"):
        from jarvis.core import approvals
        return getattr(approvals, name)
    if name == "get_all_backends":
        from jarvis.core.router import get_all_backends
        return get_all_backends
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
