"""ADB transport wrapping the adb CLI.

Supports USB (direct) and WiFi (adb connect) modes.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from .base import CommandResult, Transport, TransportError

AdbMode = Literal["usb", "wifi"]


class AdbTransport(Transport):
    """ADB transport for Android devices and embedded boards."""

    name = "adb"

    def __init__(
        self,
        mode: AdbMode,
        binary: str = "adb",
        serial: str | None = None,
        wifi_host: str | None = None,
        wifi_port: int = 5555,
        timeout: float = 15.0,
    ) -> None:
        if mode not in ("usb", "wifi"):
            raise ValueError(f"ADB mode must be usb/wifi, got {mode!r}")
        if mode == "wifi" and not wifi_host:
            raise ValueError("ADB wifi mode requires wifi_host")

        self.mode = mode
        self.binary = binary
        self.serial = serial
        self.wifi_host = wifi_host
        self.wifi_port = wifi_port
        self.timeout = timeout
        self._wifi_target = f"{wifi_host}:{wifi_port}" if mode == "wifi" else None
        self._connected = False

    def _target_args(self) -> list[str]:
        """Build device selection arguments."""
        if self.mode == "wifi":
            return ["-s", self._wifi_target]
        if self.serial:
            return ["-s", self.serial]
        return []

    async def _adb(self, args: list[str], timeout: float | None = None) -> CommandResult:
        """Execute adb command as subprocess."""
        argv = [self.binary, *self._target_args(), *args]
        to = timeout or self.timeout
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=to)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise TransportError(f"ADB command timed out after {to}s")
            return CommandResult(
                stdout=stdout.decode("utf-8", errors="replace") or "",
                stderr=stderr.decode("utf-8", errors="replace") or "",
                rc=proc.returncode or -1,
            )
        except OSError as e:
            raise TransportError(f"ADB execution failed: {e}") from e

    async def connect(self) -> None:
        """Establish ADB connection."""
        if self.mode == "wifi":
            r = await self._adb(["connect", self._wifi_target])
            if "connected" not in r.stdout.lower() and "already connected" not in r.stdout.lower():
                raise TransportError(f"ADB wifi connect failed: {r.stdout}")
            self._connected = True
        else:
            r = await self._adb(["devices"])
            if r.rc != 0:
                raise TransportError(f"ADB devices check failed: {r.stderr}")

    async def disconnect(self) -> None:
        """Disconnect ADB."""
        if self.mode == "wifi" and self._connected:
            await self._adb(["disconnect", self._wifi_target])
            self._connected = False

    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult:
        """Execute shell command via adb."""
        return await self._adb(["shell", cmd], timeout=timeout)

    async def push(self, local_path: str, remote_path: str) -> None:
        """Push file to device."""
        r = await self._adb(["push", local_path, remote_path], timeout=self.timeout * 2)
        if r.rc != 0:
            raise TransportError(f"ADB push failed: {r.stderr}")

    async def pull(self, remote_path: str, local_path: str) -> None:
        """Pull file from device."""
        r = await self._adb(["pull", remote_path, local_path], timeout=self.timeout * 2)
        if r.rc != 0:
            raise TransportError(f"ADB pull failed: {r.stderr}")

    async def is_alive(self) -> bool:
        """Check if device is reachable."""
        try:
            r = await self._adb(["get-state"])
            return "device" in r.stdout.lower()
        except TransportError:
            return False

    def describe(self) -> str:
        """Return connection description."""
        if self.mode == "wifi":
            return f"adb-wifi {self._wifi_target}"
        return f"adb-usb {self.serial or 'default'}"
