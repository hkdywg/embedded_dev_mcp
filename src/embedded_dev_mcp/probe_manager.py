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
        gdb_binary: str = "arm-none-eabi-gdb",
        gdb_port: int = 1337,
        timeout: float = 30.0,
    ) -> None:
        self.probe_type = probe_type
        self.target_chip = target_chip
        self.probe_rs_binary = probe_rs_binary
        self.gdb_binary = gdb_binary
        self.gdb_port = gdb_port
        self.timeout = timeout
        self._connected = False
        self._gdb_server_proc: asyncio.subprocess.Process | None = None

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

    async def erase_flash(self) -> str:
        """Erase all flash memory."""
        args = ["erase", "--chip", self.target_chip]

        stdout, stderr, rc = await self._run_probe_rs(args, timeout=60.0)

        if rc != 0:
            raise ProbeError(f"Erase failed: {stderr}")

        return "Flash erased successfully"

    async def program_flash(self, firmware_path: str) -> str:
        """Program firmware to flash (no verify)."""
        args = ["download", firmware_path, "--chip", self.target_chip]

        stdout, stderr, rc = await self._run_probe_rs(args, timeout=120.0)

        if rc != 0:
            raise ProbeError(f"Program failed: {stderr}")

        return f"Programmed {firmware_path} successfully"

    async def verify_flash(self, firmware_path: str) -> str:
        """Verify flash contents against firmware file."""
        args = ["verify", firmware_path, "--chip", self.target_chip]

        stdout, stderr, rc = await self._run_probe_rs(args, timeout=60.0)

        if rc != 0:
            raise ProbeError(f"Verify failed: {stderr}")

        return f"Verified {firmware_path} successfully"

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

    async def start_gdb_server(self) -> str:
        """Start probe-rs GDB server in background."""
        if self._gdb_server_proc and self._gdb_server_proc.returncode is None:
            return "GDB server already running"

        args = ["gdb", "--chip", self.target_chip, "--port", str(self.gdb_port)]
        try:
            self._gdb_server_proc = await asyncio.create_subprocess_exec(
                self.probe_rs_binary,
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as e:
            raise ProbeError(f"Failed to start GDB server: {e}")

        await asyncio.sleep(0.5)
        return f"GDB server started on port {self.gdb_port}"

    async def stop_gdb_server(self) -> str:
        """Stop the GDB server."""
        if not self._gdb_server_proc or self._gdb_server_proc.returncode is not None:
            return "GDB server not running"

        self._gdb_server_proc.terminate()
        await self._gdb_server_proc.wait()
        self._gdb_server_proc = None
        return "GDB server stopped"

    async def _run_gdb(
        self, commands: list[str], timeout: float = 10.0
    ) -> tuple[str, str, int]:
        """Execute GDB commands in batch mode against the GDB server."""
        argv = [
            self.gdb_binary,
            "-batch",
            "-ex", f"target remote localhost:{self.gdb_port}",
        ]
        for cmd in commands:
            argv.extend(["-ex", cmd])
        argv.extend(["-ex", "quit"])

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
            raise ProbeError(f"GDB timed out after {to}s")
        except FileNotFoundError:
            raise ProbeError(f"GDB binary not found: {self.gdb_binary}")

    async def set_breakpoint(self, address: int, hw: bool = True) -> str:
        """Set a breakpoint. hw=True for hardware breakpoint (hbreak)."""
        cmd = f"hbreak *0x{address:08X}" if hw else f"break *0x{address:08X}"
        stdout, stderr, rc = await self._run_gdb([cmd])

        if rc != 0 and "Breakpoint" not in stdout:
            raise ProbeError(f"Set breakpoint failed: {stderr or stdout}")

        return f"Breakpoint set at 0x{address:08X}"

    async def clear_breakpoint(self, address: int) -> str:
        """Clear breakpoint at address."""
        stdout, stderr, rc = await self._run_gdb([f"clear *0x{address:08X}"])

        if rc != 0 and "Deleted" not in stdout:
            raise ProbeError(f"Clear breakpoint failed: {stderr or stdout}")

        return f"Breakpoint cleared at 0x{address:08X}"

    async def list_breakpoints(self) -> str:
        """List all breakpoints."""
        stdout, stderr, rc = await self._run_gdb(["info breakpoints"])

        if rc != 0:
            raise ProbeError(f"List breakpoints failed: {stderr}")

        if "No breakpoints" in stdout:
            return "No breakpoints set"

        return stdout

    async def clear_all_breakpoints(self) -> str:
        """Clear all breakpoints."""
        stdout, stderr, rc = await self._run_gdb(["delete"])

        if rc != 0:
            raise ProbeError(f"Clear breakpoints failed: {stderr}")

        return "All breakpoints cleared"

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
