from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Hashable, Optional, TypeVar

V = TypeVar("V")
K = TypeVar("K", bound=Hashable)


class CacheInterface(ABC):
    """Abstract async cache interface.

    Implementations should be safe to use from async code and provide a
    `get_or_load` helper that prevents duplicate concurrent loads for the
    same key.
    """

    @abstractmethod
    async def get(self, key: K) -> Optional[V]:
        pass

    @abstractmethod
    async def set(self, key: K, value: V) -> None:
        pass

    @abstractmethod
    async def delete(self, key: K) -> None:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass
