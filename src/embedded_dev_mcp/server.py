"""MCP server implementation with main entry point.

This is the single entry point for the embedded-dev-mcp server.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .audit import AuditLog
from .config import Settings
from .safety import READ_PATH_ROOTS, WRITE_PATH_ROOTS, check_path, check_shell_prefix
from .tools import ReadOnlyTools, WritableTools
from .transports import build_transport


def create_server(settings: Settings) -> FastMCP:
    """Create and configure the MCP server."""
    transport = build_transport(settings)
    audit = AuditLog(settings.audit_log_path)
    ro = ReadOnlyTools(transport, audit, extra_prefixes=settings.extra_prefixes)
    rw = WritableTools(transport, audit)

    mcp = FastMCP(settings.server_name)

    # Read-only tools
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

    # Writable tools
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

    # ADB-specific tool (only for ADB transport)
    if transport.name == "adb":
        @mcp.tool()
        async def adb_devices() -> str:
            """List connected ADB devices."""
            from .transports.adb import AdbTransport

            adb_t = transport
            if isinstance(adb_t, AdbTransport):
                result = await adb_t._adb(["devices", "-l"])
                return result.format()
            return "Not available for this transport"

    return mcp


def main() -> int:
    """Main entry point."""
    try:
        settings = Settings.from_env()
    except Exception as e:
        print(f"[embedded-dev-mcp] Configuration error: {e}", file=sys.stderr)
        return 2

    mcp = create_server(settings)
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
