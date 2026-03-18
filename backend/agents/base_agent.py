import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import ClassVar

from langchain_core.language_models import BaseChatModel

from backend.domain.base import BaseEntity
from backend.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all LLM-powered agents in the pipeline."""

    agent_name: ClassVar[str]

    def __init__(self, llm: BaseChatModel, tools: dict[str, BaseTool] | None = None) -> None:
        self._llm = llm
        self._tools: dict[str, BaseTool] = tools or {}

    @abstractmethod
    async def run(self, input: BaseEntity) -> BaseEntity:
        """Execute the agent's task. Must not raise — return degraded model on failure."""
        ...

    @abstractmethod
    def validate_input(self, input: BaseEntity) -> bool:
        """Return True if `input` satisfies this agent's preconditions."""
        ...

    @asynccontextmanager
    async def _timed_call(self, task_name: str):
        """Context manager for automatic LLM call timing and logging."""
        start = time.monotonic()
        logger.info("[%s] starting '%s'", self.agent_name, task_name)
        try:
            yield
        finally:
            elapsed = time.monotonic() - start
            logger.info("[%s] finished '%s' in %.2fs", self.agent_name, task_name, elapsed)
