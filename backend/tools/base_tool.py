import asyncio
import functools
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import ClassVar, Optional

logger = logging.getLogger(__name__)

_cache: dict[str, Optional[dict]] = {}


def cached_call(ttl: int = 300):
    """Decorator: cache tool results by hashed kwargs for `ttl` seconds."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, **kwargs):
            key = hashlib.sha256(
                json.dumps({"tool": self.tool_name, **kwargs}, sort_keys=True).encode()
            ).hexdigest()
            if key in _cache:
                logger.debug("Cache hit for %s (key=%s)", self.tool_name, key[:8])
                return _cache[key]
            result = await func(self, **kwargs)
            _cache[key] = result
            return result

        return wrapper

    return decorator


class BaseTool(ABC):
    """Abstract base for all external I/O tool wrappers."""

    tool_name: ClassVar[str]

    @abstractmethod
    async def call(self, **kwargs) -> Optional[dict]:
        """Execute the tool. Returns None on any failure — never raises."""
        ...
