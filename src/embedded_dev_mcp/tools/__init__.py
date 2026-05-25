"""Tools module initialization."""

from __future__ import annotations

from ..audit import AuditLog
from ..safety import quote
from ..transports.base import Transport, TransportError


class ReadOnlyTools:
    """Read-only tools for device interaction."""

    def __init__(
        self,
        transport: Transport,
        audit: AuditLog,
        extra_prefixes: tuple[str, ...] = (),
    ) -> None:
        self.transport = transport
        self.audit = audit
        self.extra_prefixes = extra_prefixes

    async def _run(self, cmd: str, tool: str, args: dict, timeout: float | None = None) -> str:
        try:
            result = await self.transport.run(cmd, timeout=timeout)
        except TransportError as e:
            msg = f"DEVICE_UNREACHABLE: {e}"
            self.audit.write(tool, args, msg, ok=False)
            return msg
        out = result.format()
        self.audit.write(tool, args, out[:200], rc=result.rc, ok=(result.rc == 0))
        return out

    async def device_info(self) -> str:
        cmd = (
            "echo '=== TRANSPORT ===' && echo '{t}' && "
            "echo '=== UNAME ===' && uname -a && "
            "echo '=== UPTIME ===' && uptime && "
            "echo '=== HOSTNAME ===' && hostname"
        ).replace("{t}", self.transport.describe())
        return await self._run(cmd, "device_info", {})

    async def read_dmesg(self, lines: int = 100, grep: str | None = None) -> str:
        lines = max(1, min(int(lines), 5000))
        if grep:
            cmd = f"dmesg | grep -E {quote(grep)} | tail -n {lines}"
        else:
            cmd = f"dmesg | tail -n {lines}"
        return await self._run(cmd, "read_dmesg", {"lines": lines, "grep": grep})

    async def read_sysfs(self, path: str) -> str:
        return await self._run(f"cat {quote(path)}", "read_sysfs", {"path": path})

    async def read_proc(self, path: str) -> str:
        return await self._run(f"cat {quote(path)}", "read_proc", {"path": path})

    async def list_dir(self, path: str, long: bool = False) -> str:
        cmd = f"ls {'-la' if long else '-a'} {quote(path)}"
        return await self._run(cmd, "list_dir", {"path": path, "long": long})

    async def lsmod(self) -> str:
        return await self._run("lsmod", "lsmod", {})

    async def modinfo(self, module: str) -> str:
        return await self._run(f"modinfo {quote(module)}", "modinfo", {"module": module})

    async def read_gpio(self, gpio: int) -> str:
        return await self._run(f"cat /sys/class/gpio/gpio{gpio}/value", "read_gpio", {"gpio": gpio})

    async def read_iio(self, device: str, channel: str) -> str:
        return await self._run(
            f"cat /sys/bus/iio/devices/{quote(device)}/{quote(channel)}",
            "read_iio",
            {"device": device, "channel": channel},
        )

    async def run_shell(self, cmd: str) -> str:
        from ..safety import check_shell_prefix

        ok, reason = check_shell_prefix(cmd, self.extra_prefixes)
        if not ok:
            self.audit.write("run_shell", {"cmd": cmd[:50]}, f"REJECTED: {reason}", ok=False)
            return f"REJECTED: {reason}"
        return await self._run(cmd, "run_shell", {"cmd": cmd[:100]})


class WritableTools:
    """Writable tools that modify device state."""

    def __init__(self, transport: Transport, audit: AuditLog) -> None:
        self.transport = transport
        self.audit = audit

    async def _run(self, cmd: str, tool: str, args: dict, timeout: float = 30.0) -> str:
        try:
            result = await self.transport.run(cmd, timeout=timeout)
        except TransportError as e:
            msg = f"DEVICE_UNREACHABLE: {e}"
            self.audit.write(tool, args, msg, ok=False)
            return msg
        out = result.format()
        self.audit.write(tool, args, out[:200], rc=result.rc, ok=(result.rc == 0))
        return out

    async def install_module(self, ko_path: str, params: str = "") -> str:
        import os
        import re

        _mod_re = re.compile(r"^[A-Za-z0-9_\.\-]+$")
        if not ko_path.endswith(".ko"):
            return "REJECTED: ko_path must end with .ko"
        if not os.path.isfile(ko_path):
            return f"REJECTED: local file not found: {ko_path}"
        if any(c in params for c in (";", "&", "|", "<", ">", "\n", "`", "$(")):
            return "REJECTED: params contains shell metacharacters"

        remote = f"/tmp/{os.path.basename(ko_path)}"
        try:
            await self.transport.push(ko_path, remote)
        except TransportError as e:
            self.audit.write("install_module", {"ko": ko_path}, str(e), ok=False)
            return f"PUSH_FAILED: {e}"

        cmd = f"insmod {quote(remote)} {params}".strip()
        return await self._run(cmd, "install_module", {"ko_path": ko_path, "remote": remote})

    async def remove_module(self, name: str) -> str:
        import re

        _mod_re = re.compile(r"^[A-Za-z0-9_\-]+$")
        if not _mod_re.match(name):
            return "REJECTED: module name invalid"
        return await self._run(f"rmmod {quote(name)}", "remove_module", {"name": name})

    async def write_sysfs(self, path: str, value: str) -> str:
        if any(c in value for c in (";", "&", "|", "<", ">", "\n", "`", "$(")):
            return "REJECTED: value contains shell metacharacters"
        cmd = f"echo {quote(value)} > {quote(path)}"
        return await self._run(cmd, "write_sysfs", {"path": path, "value": value[:50]})

    async def set_gpio(self, gpio: int, value: int) -> str:
        value = max(0, min(int(value), 1))
        return await self._run(
            f"echo {value} > /sys/class/gpio/gpio{gpio}/value",
            "set_gpio",
            {"gpio": gpio, "value": value},
        )

    async def export_gpio(self, gpio: int) -> str:
        return await self._run(
            f"echo {gpio} > /sys/class/gpio/export",
            "export_gpio",
            {"gpio": gpio},
        )

    async def reboot_device(self) -> str:
        return await self._run("reboot", "reboot_device", {}, timeout=5.0)

    async def pull_file(self, remote_path: str, local_path: str) -> str:
        import os

        if not os.path.isdir(os.path.dirname(local_path)):
            return "REJECTED: local parent directory not found"
        try:
            await self.transport.pull(remote_path, local_path)
            self.audit.write(
                "pull_file",
                {"remote": remote_path, "local": local_path},
                "ok",
                ok=True,
            )
            return f"Pulled {remote_path} -> {local_path}"
        except TransportError as e:
            self.audit.write(
                "pull_file",
                {"remote": remote_path, "local": local_path},
                str(e),
                ok=False,
            )
            return f"PULL_FAILED: {e}"
