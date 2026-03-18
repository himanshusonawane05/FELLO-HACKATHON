import asyncio
from typing import Optional

from backend.domain.intelligence import AccountIntelligence
from backend.storage.base import AbstractAccountStore


class InMemoryAccountStore(AbstractAccountStore):
    """Thread-safe, asyncio-compatible in-memory account intelligence store."""

    def __init__(self) -> None:
        self._store: dict[str, AccountIntelligence] = {}
        self._lock = asyncio.Lock()

    async def save(self, intelligence: AccountIntelligence) -> str:
        """Persist an AccountIntelligence object. Returns its ID."""
        async with self._lock:
            self._store[intelligence.id] = intelligence
        return intelligence.id

    async def get(self, account_id: str) -> Optional[AccountIntelligence]:
        """Retrieve account intelligence by ID. Returns None if not found."""
        async with self._lock:
            return self._store.get(account_id)

    async def list(self, page: int = 1, size: int = 20) -> tuple[list[AccountIntelligence], int]:
        """Return a paginated list of all account intelligence records."""
        async with self._lock:
            all_items = sorted(
                self._store.values(),
                key=lambda a: a.analyzed_at,
                reverse=True,
            )
        total = len(all_items)
        start = (page - 1) * size
        return all_items[start : start + size], total


account_store = InMemoryAccountStore()
