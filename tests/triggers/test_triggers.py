import pytest
import asyncio
from jarvis.triggers.base import Trigger, CronTrigger, TriggerManager

class DummyTrigger(Trigger):
    async def start(self):
        await super().start()

    async def stop(self):
        await super().stop()

@pytest.mark.asyncio
async def test_trigger_firing():
    fired = False
    payload_received = None

    def callback(name, payload):
        nonlocal fired, payload_received
        fired = True
        payload_received = payload

    trigger = DummyTrigger("dummy")
    trigger.attach(callback)
    
    await trigger.fire({"msg": "hello"})
    
    assert fired is True
    assert payload_received == {"msg": "hello"}

@pytest.mark.asyncio
async def test_async_callback():
    fired = False

    async def async_callback(name, payload):
        nonlocal fired
        await asyncio.sleep(0.01)
        fired = True

    trigger = DummyTrigger("dummy_async")
    trigger.attach(async_callback)
    
    await trigger.fire({})
    assert fired is True

@pytest.mark.asyncio
async def test_cron_trigger():
    fired_count = 0

    def callback(name, payload):
        nonlocal fired_count
        fired_count += 1

    # Short interval for testing
    trigger = CronTrigger("test_cron", 0.1)
    trigger.attach(callback)
    
    await trigger.start()
    
    # Wait long enough for 2 fires
    await asyncio.sleep(0.25)
    
    await trigger.stop()
    
    # Should have fired at least twice
    assert fired_count >= 2

@pytest.mark.asyncio
async def test_trigger_manager():
    manager = TriggerManager()
    t1 = DummyTrigger("t1")
    t2 = DummyTrigger("t2")
    
    manager.register(t1)
    manager.register(t2)
    
    assert manager.get_trigger("t1") == t1
    assert manager.get_trigger("t2") == t2
    
    await manager.start_all()
    assert t1._running is True
    assert t2._running is True
    
    await manager.stop_all()
    assert t1._running is False
    assert t2._running is False
