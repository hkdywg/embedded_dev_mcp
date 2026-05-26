"""MCU debugging tools for embedded development.

These tools wrap probe-rs for operations like:
- Flash programming
- Memory/register access
- Breakpoint management
- RTT logging
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..audit import AuditLog
from ..probe_manager import ProbeError, ProbeRsManager


class McuDebugTools:
    """MCU debugging tools using probe-rs."""

    def __init__(
        self,
        probe_manager: ProbeRsManager,
        audit: AuditLog,
    ) -> None:
        self.probe = probe_manager
        self.audit = audit

    async def _run(self, operation: str, args: dict, result: str, ok: bool = True) -> str:
        self.audit.write(operation, args, result[:200], ok=ok)
        return result

    # Probe management
    async def list_probes(self) -> str:
        """List all connected debug probes."""
        try:
            probes = await self.probe.list_probes()
            if not probes:
                return await self._run("list_probes", {}, "No probes found")
            lines = [f"{p.index}: {p.vendor} {p.product} (Serial: {p.serial})" for p in probes]
            return await self._run("list_probes", {"count": len(probes)}, "\n".join(lines))
        except ProbeError as e:
            return await self._run("list_probes", {}, f"ERROR: {e}", ok=False)

    async def connect_probe(self, probe_index: int | None = None) -> str:
        """Connect to a debug probe."""
        try:
            result = await self.probe.connect(probe_index)
            return await self._run("connect_probe", {"probe_index": probe_index}, result)
        except ProbeError as e:
            return await self._run("connect_probe", {"probe_index": probe_index}, f"ERROR: {e}", ok=False)

    # Flash operations
    async def flash_firmware(self, firmware_path: str, verify: bool = True) -> str:
        """Flash firmware to the target MCU."""
        path = Path(firmware_path)
        if not path.exists():
            return await self._run("flash_firmware", {"path": firmware_path}, f"File not found: {firmware_path}", ok=False)
        if not firmware_path.endswith((".elf", ".hex", ".bin")):
            return await self._run("flash_firmware", {"path": firmware_path}, "Invalid format. Use ELF, HEX, or BIN.", ok=False)

        try:
            result = await self.probe.flash(firmware_path, verify=verify)
            return await self._run("flash_firmware", {"path": firmware_path, "verify": verify}, result)
        except ProbeError as e:
            return await self._run("flash_firmware", {"path": firmware_path}, f"ERROR: {e}", ok=False)

    async def erase_flash(self) -> str:
        """Erase all flash memory."""
        try:
            result = await self.probe.erase_flash()
            return await self._run("erase_flash", {}, result)
        except ProbeError as e:
            return await self._run("erase_flash", {}, f"ERROR: {e}", ok=False)

    # Target control
    async def reset_target(self, halt: bool = False) -> str:
        """Reset the target MCU."""
        try:
            result = await self.probe.reset(halt=halt)
            return await self._run("reset_target", {"halt": halt}, result)
        except ProbeError as e:
            return await self._run("reset_target", {"halt": halt}, f"ERROR: {e}", ok=False)

    async def halt_target(self) -> str:
        """Halt the target MCU."""
        try:
            result = await self.probe.halt()
            return await self._run("halt_target", {}, result)
        except ProbeError as e:
            return await self._run("halt_target", {}, f"ERROR: {e}", ok=False)

    async def resume_target(self) -> str:
        """Resume target execution."""
        try:
            result = await self.probe.run()
            return await self._run("resume_target", {}, result)
        except ProbeError as e:
            return await self._run("resume_target", {}, f"ERROR: {e}", ok=False)

    async def run_target(self) -> str:
        """Run (resume) target execution after halt."""
        try:
            result = await self.probe.run()
            return await self._run("run_target", {}, result)
        except ProbeError as e:
            return await self._run("run_target", {}, f"ERROR: {e}", ok=False)

    async def step_target(self) -> str:
        """Single-step target execution."""
        try:
            result = await self.probe.step()
            return await self._run("step_target", {}, result)
        except ProbeError as e:
            return await self._run("step_target", {}, f"ERROR: {e}", ok=False)

    # Memory operations
    async def read_memory(self, address: int, size: int, format: str = "hex") -> str:
        """Read memory from target MCU."""
        address = max(0, int(address))
        size = max(1, min(int(size), 4096))
        format = format.lower()
        if format not in ("hex", "bin", "ascii"):
            return await self._run("read_memory", {}, "Invalid format. Use hex, bin, or ascii.", ok=False)

        try:
            result = await self.probe.read_memory(address, size, format)
            return await self._run("read_memory", {"address": address, "size": size}, result)
        except ProbeError as e:
            return await self._run("read_memory", {"address": address}, f"ERROR: {e}", ok=False)

    async def write_memory(self, address: int, data: str, format: str = "hex") -> str:
        """Write memory to target MCU."""
        address = max(0, int(address))
        format = format.lower()
        if format not in ("hex", "bin"):
            return await self._run("write_memory", {}, "Invalid format. Use hex or bin.", ok=False)

        try:
            result = await self.probe.write_memory(address, data, format)
            return await self._run("write_memory", {"address": address, "size": len(data)}, result)
        except ProbeError as e:
            return await self._run("write_memory", {"address": address}, f"ERROR: {e}", ok=False)

    # Target info
    async def target_info(self) -> str:
        """Get target MCU information."""
        try:
            result = await self.probe.info()
            return await self._run("target_info", {}, result)
        except ProbeError as e:
            return await self._run("target_info", {}, f"ERROR: {e}", ok=False)


class RttTools:
    """RTT (Real-Time Transfer) logging tools."""

    def __init__(self, probe_manager: ProbeRsManager, audit: AuditLog) -> None:
        self.probe = probe_manager
        self.audit = audit
        self._rtt_attached = False

    async def rtt_attach(self) -> str:
        """Attach to RTT channel."""
        try:
            stdout, stderr, rc = await self.probe._run_probe_rs(["rtt", "attach"])
            if rc != 0:
                self.audit.write("rtt_attach", {}, stderr[:200], ok=False)
                return f"ERROR: {stderr}"
            self._rtt_attached = True
            self.audit.write("rtt_attach", {}, "RTT attached", ok=True)
            return "RTT attached"
        except ProbeError as e:
            self.audit.write("rtt_attach", {}, str(e), ok=False)
            return f"ERROR: {e}"

    async def rtt_read(self, channel: int = 0, timeout: float = 5.0) -> str:
        """Read from RTT channel."""
        if not self._rtt_attached:
            return "RTT not attached. Call rtt_attach first."

        try:
            stdout, stderr, rc = await self.probe._run_probe_rs(
                ["rtt", "read", "--channel", str(channel)],
                timeout=timeout,
            )
            self.audit.write("rtt_read", {"channel": channel}, stdout[:200], ok=(rc == 0))
            return stdout if rc == 0 else f"ERROR: {stderr}"
        except ProbeError as e:
            self.audit.write("rtt_read", {"channel": channel}, str(e), ok=False)
            return f"ERROR: {e}"

    async def rtt_detach(self) -> str:
        """Detach from RTT."""
        try:
            stdout, stderr, rc = await self.probe._run_probe_rs(["rtt", "detach"])
            self._rtt_attached = False
            self.audit.write("rtt_detach", {}, "RTT detached", ok=(rc == 0))
            return "RTT detached" if rc == 0 else f"ERROR: {stderr}"
        except ProbeError as e:
            self.audit.write("rtt_detach", {}, str(e), ok=False)
            return f"ERROR: {e}"


class SerialMonitorTools:
    """Serial port monitoring tools."""

    def __init__(self, audit: AuditLog) -> None:
        self.audit = audit
        self._serial_port: str | None = None
        self._baud_rate: int = 115200

    async def list_serial_ports(self) -> str:
        """List available serial ports."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "serial.tools.list_ports",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            result = stdout.decode() if proc.returncode == 0 else stderr.decode()
            self.audit.write("list_serial_ports", {}, result[:200], ok=(proc.returncode == 0))
            return result
        except Exception as e:
            self.audit.write("list_serial_ports", {}, str(e), ok=False)
            return f"ERROR: {e}"

    async def monitor_serial(self, port: str, baud: int = 115200, duration: float = 10.0) -> str:
        """Monitor serial port for duration."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "serial.tools.miniterm", port, str(baud),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=duration)
            except asyncio.TimeoutError:
                proc.terminate()
                await proc.wait()
                stdout = b"[Monitor stopped after timeout]"

            result = stdout.decode()
            self.audit.write("monitor_serial", {"port": port, "baud": baud}, result[:200])
            return result
        except Exception as e:
            self.audit.write("monitor_serial", {"port": port}, str(e), ok=False)
            return f"ERROR: {e}"
