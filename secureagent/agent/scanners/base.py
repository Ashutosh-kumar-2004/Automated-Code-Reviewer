"""
Base class definition for security vulnerability scanners.
"""
from abc import ABC, abstractmethod
from agent.schemas import RawFinding


class BaseScanner(ABC):
    """Abstract interface that all static and dynamic scanners implement."""

    name: str = "base"

    @abstractmethod
    async def scan(self, workspace_path: str) -> list[RawFinding]:
        """Execute scanner against the target workspace directory and return RawFindings."""
        pass
