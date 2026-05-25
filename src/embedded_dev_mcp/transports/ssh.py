"""SSH transport using asyncssh.

Connections are per-call (short-lived) to survive device reboots.
"""

from __future__ import annotations

import asyncio

import asyncssh

from .base import CommandResult, Transport, TransportError


class SshTransport(Transport):
    """SSH transport for embedded Linux devices."""

    name = "ssh"

    def __init__(
        self,
        host: str,
        port: int = 22,
        user: str = "root",
        key: str | None = None,
        password: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.key = key
        self.password = password
        self.timeout = timeout

    async def connect(self) -> None:
        """Verify connection during startup."""
        async with await self._open():
            return

    async def disconnect(self) -> None:
        """No persistent connection to close."""
        return

    def _connect_kwargs(self) -> dict:
        """Build asyncssh connect arguments."""
        kw: dict = {
            "host": self.host,
            "port": self.port,
            "username": self.user,
            "known_hosts": None,
        }
        if self.key:
            kw["client_keys"] = [self.key]
        if self.password:
            kw["password"] = self.password
        return kw

    async def _open(self):
        """Open SSH connection with timeout."""
        try:
            return await asyncio.wait_for(
                asyncssh.connect(**self._connect_kwargs()),
                timeout=self.timeout,
            )
        except (OSError, asyncssh.Error, asyncio.TimeoutError) as e:
            raise TransportError(
                f"SSH connect to {self.user}@{self.host}:{self.port} failed: {e}"
            ) from e

    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult:
        """Execute command over SSH."""
        to = timeout or self.timeout
        try:
            async with await self._open() as conn:
                r = await asyncio.wait_for(conn.run(cmd, check=False), timeout=to)
                return CommandResult(
                    stdout=r.stdout or "",
                    stderr=r.stderr or "",
                    rc=int(r.exit_status if r.exit_status is not None else -1),
                )
        except asyncio.TimeoutError as e:
            raise TransportError(f"SSH command timed out after {to}s: {cmd[:120]}") from e
        except asyncssh.Error as e:
            raise TransportError(f"SSH run failed: {e}") from e

    async def push(self, local_path: str, remote_path: str) -> None:
        """SCP push file to device."""
        try:
            async with await self._open() as conn:
                await asyncio.wait_for(
                    asyncssh.scp(local_path, (conn, remote_path)),
                    timeout=self.timeout * 2,
                )
        except (asyncssh.Error, asyncio.TimeoutError, OSError) as e:
            raise TransportError(f"SCP push failed: {e}") from e

    async def pull(self, remote_path: str, local_path: str) -> None:
        """SCP pull file from device."""
        try:
            async with await self._open() as conn:
                await asyncio.wait_for(
                    asyncssh.scp((conn, remote_path), local_path),
                    timeout=self.timeout * 2,
                )
        except (asyncssh.Error, asyncio.TimeoutError, OSError) as e:
            raise TransportError(f"SCP pull failed: {e}") from e

    async def is_alive(self) -> bool:
        """Check if SSH connection works."""
        try:
            async with await self._open():
                return True
        except TransportError:
            return False

    def describe(self) -> str:
        """Return connection description."""
        return f"ssh {self.user}@{self.host}:{self.port}"
