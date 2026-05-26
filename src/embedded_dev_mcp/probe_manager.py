"""Probe-rs manager for MCU debugging.

This module wraps the probe-rs CLI tool for embedded debugging operations.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Literal

ProbeType = Literal["stlink", "jlink", "daplink", "blackmagic"]
TargetArch = Literal["arm", "riscv"]


@dataclass
class ProbeInfo:
    """Information about a connected debug probe."""
    index: int
    vendor: str
    product: str
    serial: str


class ProbeRsManager:
    """Manages probe-rs CLI interactions for MCU debugging."""

    def __init__(
        self,
        probe_type: ProbeType = "stlink",
        target_chip: str = "stm32f4",
        probe_rs_binary: str = "probe-rs",
        timeout: float = 30.0,
    ) -> None:
        self.probe_type = probe_type
        self.target_chip = target_chip
        self.probe_rs_binary = probe_rs_binary
        self.timeout = timeout
        self._connected = False
        self._session_id: str | None = None

    async def _run_probe_rs(
        self,
        args: list[str],
        timeout: float | None = None,
    ) -> tuple[str, str, int]:
        """Execute probe-rs command and return stdout, stderr, exit_code."""
        argv = [self.probe_rs_binary, *args]
        to = timeout or self.timeout

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=to)
            return (
                stdout.decode("utf-8", errors="replace") or "",
                stderr.decode("utf-8", errors="replace") or "",
                proc.returncode or -1,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise ProbeError(f"probe-rs timed out after {to}s")
        except FileNotFoundError:
            raise ProbeError(f"probe-rs binary not found: {self.probe_rs_binary}")

    async def list_probes(self) -> list[ProbeInfo]:
        """List all connected debug probes."""
        stdout, stderr, rc = await self._run_probe_rs(["list"])

        if rc != 0:
            raise ProbeError(f"Failed to list probes: {stderr}")

        probes = []
        for line in stdout.splitlines():
            match = re.match(r"(\d+):\s*(.+?)\s*\((.+?)\)\s*Serial:\s*(.+)", line)
            if match:
                probes.append(ProbeInfo(
                    index=int(match.group(1)),
                    vendor=match.group(2).strip(),
                    product=match.group(3).strip(),
                    serial=match.group(4).strip(),
                ))
        return probes

    async def connect(self, probe_index: int | None = None) -> str:
        """Connect to a debug probe."""
        args = ["connect"]
        if probe_index is not None:
            args.extend(["--probe", str(probe_index)])
        args.extend(["--chip", self.target_chip])

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Failed to connect: {stderr}")

        self._connected = True
        return f"Connected to {self.target_chip} via {self.probe_type}"

    async def flash(self, firmware_path: str, verify: bool = True) -> str:
        """Flash firmware to the target."""
        args = ["download", firmware_path]
        args.extend(["--chip", self.target_chip])
        if verify:
            args.append("--verify")

        stdout, stderr, rc = await self._run_probe_rs(args, timeout=120.0)

        if rc != 0:
            raise ProbeError(f"Flash failed: {stderr}")

        return f"Flashed {firmware_path} successfully"

    async def erase_flash(self) -> str:
        """Erase all flash memory."""
        args = ["erase", "--chip", self.target_chip]

        stdout, stderr, rc = await self._run_probe_rs(args, timeout=60.0)

        if rc != 0:
            raise ProbeError(f"Erase failed: {stderr}")

        return "Flash erased successfully"

    async def reset(self, halt: bool = False) -> str:
        """Reset the target."""
        args = ["reset"]
        if halt:
            args.append("--halt")

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Reset failed: {stderr}")

        return "Target reset"

    async def halt(self) -> str:
        """Halt the target."""
        args = ["halt"]

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Halt failed: {stderr}")

        return "Target halted"

    async def run(self) -> str:
        """Resume target execution."""
        args = ["run"]

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Run failed: {stderr}")

        return "Target running"

    async def step(self) -> str:
        """Single step execution."""
        args = ["step"]

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Step failed: {stderr}")

        return "Single step completed"

    async def read_memory(self, address: int, size: int, format: str = "hex") -> str:
        """Read memory from target."""
        args = ["read", str(address), str(size)]
        args.extend(["--format", format])

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Read memory failed: {stderr}")

        return stdout

    async def write_memory(self, address: int, data: str, format: str = "hex") -> str:
        """Write memory to target."""
        args = ["write", str(address), data]
        args.extend(["--format", format])

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Write memory failed: {stderr}")

        return f"Wrote to address 0x{address:08X}"

    async def info(self) -> str:
        """Get target information."""
        args = ["info"]

        stdout, stderr, rc = await self._run_probe_rs(args)

        if rc != 0:
            raise ProbeError(f"Get info failed: {stderr}")

        return stdout


class ProbeError(Exception):
    """Error during probe-rs operation."""
