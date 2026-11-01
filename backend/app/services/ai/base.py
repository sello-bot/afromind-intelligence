from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

class AIProvider(ABC):
    @abstractmethod
    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError
