from abc import ABC, abstractmethod
from typing import Optional

from backend.domain.intelligence import AccountIntelligence


class AbstractJobStore(ABC):
    """Abstract interface for job persistence."""

    @abstractmethod
    async def create(self, job_id: str) -> "JobRecord": ...  # type: ignore[name-defined]

    @abstractmethod
    async def update(self, job_id: str, **fields) -> "JobRecord": ...  # type: ignore[name-defined]

    @abstractmethod
    async def get(self, job_id: str) -> Optional["JobRecord"]: ...  # type: ignore[name-defined]


class AbstractAccountStore(ABC):
    """Abstract interface for account intelligence persistence."""

    @abstractmethod
    async def save(self, intelligence: AccountIntelligence) -> str: ...

    @abstractmethod
    async def get(self, account_id: str) -> Optional[AccountIntelligence]: ...

    @abstractmethod
    async def list(self, page: int, size: int) -> tuple[list[AccountIntelligence], int]: ...
