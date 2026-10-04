import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Any, Optional, Dict

# Type alias for a trigger callback. It receives the trigger name and a payload.
TriggerCallback = Callable[[str, Dict[str, Any]], Any]

class Trigger(ABC):
    """Base class for Triggers (e.g., crons, webhooks, file watchers)."""

    def __init__(self, name: str):
        self._name = name
        self._callback: Optional[TriggerCallback] = None
        self._running = False

    @property
    def name(self) -> str:
        return self._name

    def attach(self, callback: TriggerCallback):
        """Attach a callback that will be called when the trigger fires."""
        self._callback = callback

    @abstractmethod
    async def start(self):
        """Start listening or scheduling."""
        self._running = True

    @abstractmethod
    async def stop(self):
        """Stop listening or scheduling."""
        self._running = False

    async def fire(self, payload: Dict[str, Any]):
        """Fire the trigger, calling the attached callback."""
        if self._callback:
            if asyncio.iscoroutinefunction(self._callback):
                await self._callback(self.name, payload)
            else:
                self._callback(self.name, payload)

class CronTrigger(Trigger):
    """A trigger that fires based on a time interval or cron expression."""
    
    def __init__(self, name: str, interval_seconds: int):
        super().__init__(name)
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None

    async def _loop(self):
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            if self._running:
                await self.fire({"reason": "cron", "interval": self.interval_seconds})

    async def start(self):
        await super().start()
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        await super().stop()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class TriggerManager:
    """Manages active triggers in the system."""

    def __init__(self):
        self._triggers: dict[str, Trigger] = {}

    def register(self, trigger: Trigger):
        self._triggers[trigger.name] = trigger

    def get_trigger(self, name: str) -> Optional[Trigger]:
        return self._triggers.get(name)

    async def start_all(self):
        for trigger in self._triggers.values():
            await trigger.start()

    async def stop_all(self):
        for trigger in self._triggers.values():
            await trigger.stop()
