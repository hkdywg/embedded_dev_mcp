"""Transport module initialization."""

from __future__ import annotations

from ..config import Settings
from .adb import AdbTransport
from .base import Transport
from .ssh import SshTransport


def build_transport(settings: Settings) -> Transport:
    """Build transport instance from settings."""
    if settings.transport == "ssh":
        return SshTransport(
            host=settings.ssh_host,
            port=settings.ssh_port,
            user=settings.ssh_user,
            key=settings.ssh_key,
            password=settings.ssh_password,
            timeout=settings.default_timeout,
        )
    elif settings.transport == "adb-usb":
        return AdbTransport(
            mode="usb",
            binary=settings.adb_binary,
            serial=settings.adb_serial,
            timeout=settings.default_timeout,
        )
    elif settings.transport == "adb-wifi":
        return AdbTransport(
            mode="wifi",
            binary=settings.adb_binary,
            wifi_host=settings.adb_wifi_host,
            wifi_port=settings.adb_wifi_port,
            timeout=settings.default_timeout,
        )
    else:
        raise ValueError(f"Unknown transport: {settings.transport}")
