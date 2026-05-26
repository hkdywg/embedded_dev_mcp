"""MCP server implementation with main entry point.

This is the single entry point for the embedded-dev-mcp server.
Supports both embedded Linux board debugging (SSH/ADB) and MCU debugging (probe-rs).
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .audit import AuditLog
from .config import Settings
from .probe_manager import ProbeRsManager
from .safety import READ_PATH_ROOTS, WRITE_PATH_ROOTS, check_path, check_shell_prefix
from .tools.linux_tools import ReadOnlyTools, WritableTools
from .tools.mcu_tools import McuDebugTools
from .tools.build_tools import BuildTools
from .transports import build_transport


def create_server(settings: Settings) -> FastMCP:
    """Create and configure the MCP server."""
    transport = build_transport(settings)
    audit = AuditLog(settings.audit_log_path)
    ro = ReadOnlyTools(transport, audit, extra_prefixes=settings.extra_prefixes)
    rw = WritableTools(transport, audit)

    # MCU debug tools (if enabled)
    mcu_tools = None
    build_tools = None
    if settings.mcu_debug_enabled:
        probe_manager = ProbeRsManager(
            probe_type=settings.probe_type,
            target_chip=settings.target_chip,
            probe_rs_binary=settings.probe_rs_binary,
            timeout=settings.default_timeout,
        )
        mcu_tools = McuDebugTools(probe_manager, audit)
        build_tools = BuildTools(
            audit=audit,
            iar_binary=settings.iar_build_binary,
            timeout=settings.default_timeout,
        )

    mcp = FastMCP(settings.server_name)

    # Embedded Linux Board Tools (Read-only)
    @mcp.tool()
    async def device_info() -> str:
        """Get device identity: transport type, uname, uptime, hostname."""
        return await ro.device_info()

    @mcp.tool()
    async def read_dmesg(lines: int = 100, grep: str | None = None) -> str:
        """Tail kernel log (dmesg). Optionally filter by regex."""
        return await ro.read_dmesg(lines=lines, grep=grep)

    @mcp.tool()
    async def read_sysfs(path: str) -> str:
        """Read a file under /sys/. Path must be absolute and under allowed roots."""
        ok, reason = check_path(path, READ_PATH_ROOTS)
        if not ok:
            return f"REJECTED: {reason}"
        return await ro.read_sysfs(path)

    @mcp.tool()
    async def read_proc(path: str) -> str:
        """Read a file under /proc/."""
        ok, reason = check_path(path, ("/proc",))
        if not ok:
            return f"REJECTED: {reason}"
        return await ro.read_proc(path)

    @mcp.tool()
    async def list_dir(path: str, long: bool = False) -> str:
        """List directory contents. Path must be under allowed roots."""
        ok, reason = check_path(path, READ_PATH_ROOTS)
        if not ok:
            return f"REJECTED: {reason}"
        return await ro.list_dir(path, long=long)

    @mcp.tool()
    async def lsmod() -> str:
        """List loaded kernel modules."""
        return await ro.lsmod()

    @mcp.tool()
    async def modinfo(module: str) -> str:
        """Show kernel module metadata."""
        return await ro.modinfo(module)

    @mcp.tool()
    async def read_gpio(gpio: int) -> str:
        """Read GPIO value via legacy sysfs interface."""
        return await ro.read_gpio(gpio)

    @mcp.tool()
    async def read_iio(device: str, channel: str) -> str:
        """Read IIO sensor channel value."""
        return await ro.read_iio(device, channel)

    @mcp.tool()
    async def run_shell(cmd: str) -> str:
        """Execute whitelisted shell command on device."""
        ok, reason = check_shell_prefix(cmd, settings.extra_prefixes)
        if not ok:
            return f"REJECTED: {reason}"
        return await ro.run_shell(cmd)

    # Embedded Linux Board Tools (Writable)
    @mcp.tool()
    async def install_module(ko_path: str, params: str = "") -> str:
        """Push .ko file to device and insmod it."""
        return await rw.install_module(ko_path, params=params)

    @mcp.tool()
    async def remove_module(name: str) -> str:
        """Remove kernel module by name."""
        return await rw.remove_module(name)

    @mcp.tool()
    async def write_sysfs(path: str, value: str) -> str:
        """Write value to sysfs file."""
        ok, reason = check_path(path, WRITE_PATH_ROOTS)
        if not ok:
            return f"REJECTED: {reason}"
        return await rw.write_sysfs(path, value)

    @mcp.tool()
    async def set_gpio(gpio: int, value: int) -> str:
        """Set GPIO output value (0 or 1)."""
        return await rw.set_gpio(gpio, value)

    @mcp.tool()
    async def export_gpio(gpio: int) -> str:
        """Export GPIO to sysfs interface."""
        return await rw.export_gpio(gpio)

    @mcp.tool()
    async def reboot_device() -> str:
        """Reboot the device."""
        return await rw.reboot_device()

    @mcp.tool()
    async def pull_file(remote_path: str, local_path: str) -> str:
        """Pull file from device to local machine."""
        return await rw.pull_file(remote_path, local_path)

    # MCU Debug Tools (if enabled)
    if mcu_tools:
        @mcp.tool()
        async def list_probes() -> str:
            """List all connected debug probes (J-Link, ST-Link, etc.)."""
            return await mcu_tools.list_probes()

        @mcp.tool()
        async def connect_probe(probe_index: int | None = None) -> str:
            """Connect to a debug probe for MCU debugging."""
            return await mcu_tools.connect_probe(probe_index)

        @mcp.tool()
        async def erase_flash() -> str:
            """Erase all flash memory on target MCU."""
            return await mcu_tools.erase_flash()

        @mcp.tool()
        async def program_flash(firmware_path: str) -> str:
            """Program firmware (ELF/HEX/BIN) to target MCU flash."""
            return await mcu_tools.program_flash(firmware_path)

        @mcp.tool()
        async def verify_flash(firmware_path: str) -> str:
            """Verify flash contents against firmware file."""
            return await mcu_tools.verify_flash(firmware_path)

        @mcp.tool()
        async def reset_target(halt: bool = False) -> str:
            """Reset the target MCU. Optionally halt after reset."""
            return await mcu_tools.reset_target(halt=halt)

        @mcp.tool()
        async def halt_target() -> str:
            """Halt the target MCU execution."""
            return await mcu_tools.halt_target()

        @mcp.tool()
        async def resume_target() -> str:
            """Resume target MCU execution."""
            return await mcu_tools.resume_target()

        @mcp.tool()
        async def read_memory(address: int, size: int, format: str = "hex") -> str:
            """Read memory from target MCU at specified address."""
            return await mcu_tools.read_memory(address, size, format)

        @mcp.tool()
        async def write_memory(address: int, data: str, format: str = "hex") -> str:
            """Write memory to target MCU at specified address."""
            return await mcu_tools.write_memory(address, data, format)

        @mcp.tool()
        async def target_info() -> str:
            """Get target MCU information."""
            return await mcu_tools.target_info()

        @mcp.tool()
        async def run_target() -> str:
            """Run (resume) target MCU after halt."""
            return await mcu_tools.run_target()

        @mcp.tool()
        async def step_target() -> str:
            """Single-step target MCU execution."""
            return await mcu_tools.step_target()

        @mcp.tool()
        async def set_breakpoint(address: int, hw: bool = True) -> str:
            """Set a hardware breakpoint at address. hw=False for software breakpoint."""
            return await mcu_tools.set_breakpoint(address, hw=hw)

        @mcp.tool()
        async def clear_breakpoint(address: int) -> str:
            """Clear breakpoint at address."""
            return await mcu_tools.clear_breakpoint(address)

        @mcp.tool()
        async def list_breakpoints() -> str:
            """List all breakpoints."""
            return await mcu_tools.list_breakpoints()

        @mcp.tool()
        async def clear_all_breakpoints() -> str:
            """Clear all breakpoints."""
            return await mcu_tools.clear_all_breakpoints()

    # Build tools (if enabled)
    if build_tools:
        @mcp.tool()
        async def iar_build(project_path: str, configuration: str = "Debug", clean: bool = False) -> str:
            """Build an IAR EWARM project (.ewp file)."""
            return await build_tools.iar_build(project_path, configuration, clean_first=clean)

        @mcp.tool()
        async def iar_clean(project_path: str, configuration: str = "Debug") -> str:
            """Clean an IAR EWARM project."""
            return await build_tools.iar_clean(project_path, configuration)

    return mcp


def main() -> int:
    """Main entry point."""
    try:
        settings = Settings.from_env()
    except ValueError as e:
        print(f"[embedded-dev-mcp] Configuration error: {e}", file=sys.stderr)
        return 2

    mcp = create_server(settings)
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
