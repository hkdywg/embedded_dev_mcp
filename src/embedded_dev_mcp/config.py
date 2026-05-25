"""Environment-driven configuration for embedded_dev_mcp.

All configuration is read from environment variables so the MCP client
(Claude Code / Cline / Cursor) can inject it via mcp.json `env` block.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Transport = Literal["ssh", "adb-usb", "adb-wifi"]


def _get_env(short: str, long: str, default: str = "") -> str:
    """Get env var, preferring short name over long name."""
    return os.environ.get(short) or os.environ.get(long) or default


@dataclass
class Settings:
    transport: Transport
    server_name: str

    # SSH
    ssh_host: str
    ssh_port: int
    ssh_user: str
    ssh_key: str | None
    ssh_password: str | None

    # ADB
    adb_binary: str
    adb_serial: str | None      # device serial (USB) or `host:port` (wifi)
    adb_wifi_host: str | None
    adb_wifi_port: int

    # Behavior
    default_timeout: float
    audit_log_path: Path
    allow_extra_shell_prefixes: tuple[str, ...]
    extra_prefixes: tuple[str, ...] = ()  # alias for compatibility

    @classmethod
    def from_env(cls) -> "Settings":
        transport = _get_env("TRANSPORT", "BOARD_TRANSPORT", "ssh").lower().strip()
        if transport not in ("ssh", "adb-usb", "adb-wifi"):
            raise ValueError(
                f"TRANSPORT must be one of ssh / adb-usb / adb-wifi, got {transport!r}"
            )

        extra = _get_env("EXTRA_SHELL_PREFIXES", "BOARD_EXTRA_SHELL_PREFIXES", "")
        extra_prefixes = tuple(p.strip() for p in extra.split(",") if p.strip())

        audit_log_default = str(Path.home() / ".embedded_dev_mcp" / "audit.log")
        audit_log_path = Path(
            os.environ.get("AUDIT_LOG") or os.environ.get("BOARD_AUDIT_LOG") or audit_log_default
        ).expanduser()

        return cls(
            transport=transport,  # type: ignore[arg-type]
            server_name=_get_env("SERVER_NAME", "BOARD_NAME", "embedded-dev"),
            ssh_host=_get_env("SSH_HOST", "BOARD_HOST", "192.168.7.2"),
            ssh_port=int(_get_env("SSH_PORT", "BOARD_PORT", "22")),
            ssh_user=_get_env("SSH_USER", "BOARD_USER", "root"),
            ssh_key=_get_env("SSH_KEY", "BOARD_KEY") or None,
            ssh_password=_get_env("SSH_PASSWORD", "BOARD_PASSWORD") or None,
            adb_binary=os.environ.get("ADB_BINARY", "adb"),
            adb_serial=os.environ.get("ADB_SERIAL") or None,
            adb_wifi_host=os.environ.get("ADB_WIFI_HOST") or None,
            adb_wifi_port=int(os.environ.get("ADB_WIFI_PORT", "5555")),
            default_timeout=float(_get_env("DEVICE_TIMEOUT", "BOARD_TIMEOUT", "15")),
            audit_log_path=audit_log_path,
            allow_extra_shell_prefixes=extra_prefixes,
            extra_prefixes=extra_prefixes,
        )
