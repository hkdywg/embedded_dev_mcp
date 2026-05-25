"""Transport abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class TransportError(Exception):
    """Transport layer failure."""


@dataclass
class CommandResult:
    """Command execution result."""

    stdout: str
    stderr: str
    rc: int

    def format(self) -> str:
        """Format result for display."""
        out = f"[exit={self.rc}]\n{self.stdout}"
        if self.stderr:
            out += f"\n[stderr]\n{self.stderr}"
        return out


class Transport(ABC):
    """Abstract transport interface for SSH/ADB."""

    name: str = "base"

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection (for startup check)."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        ...

    @abstractmethod
    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult:
        """Execute shell command."""
        ...

    @abstractmethod
    async def push(self, local_path: str, remote_path: str) -> None:
        """Push file to device."""
        ...

    @abstractmethod
    async def pull(self, remote_path: str, local_path: str) -> None:
        """Pull file from device."""
        ...

    @abstractmethod
    async def is_alive(self) -> bool:
        """Check if connection is alive."""
        ...

    @abstractmethod
    def describe(self) -> str:
        """Human-readable connection description."""
        ...
