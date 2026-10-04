import pytest
import jarvis.core
import jarvis.storage


def test_core_init_lazy_getattr():
    assert jarvis.core.JarvisAgent is not None
    assert jarvis.core.get_all_backends is not None
    assert jarvis.core.PENDING_APPROVALS is not None
    assert jarvis.core.APPROVAL_RESULTS is not None

    with pytest.raises(AttributeError, match="has no attribute 'non_existent'"):
        _ = jarvis.core.non_existent


def test_storage_init_lazy_getattr():
    assert jarvis.storage.MemoryManager is not None
    assert jarvis.storage.init_db is not None
    assert jarvis.storage.log_action is not None
    assert jarvis.storage.log_conversation is not None
    assert jarvis.storage.log_token_usage is not None
    assert jarvis.storage.build_fts_query is not None

    with pytest.raises(AttributeError, match="has no attribute 'unknown_symbol'"):
        _ = jarvis.storage.unknown_symbol
