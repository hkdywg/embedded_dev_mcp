"""Tests for config module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from embedded_dev_mcp.config import Settings


def make_env(**kwargs) -> dict:
    """Build env dict with defaults overridden by kwargs."""
    base = {
        "TRANSPORT": "ssh",
        "SSH_HOST": "10.0.0.1",
        "SSH_USER": "root",
        "SSH_KEY": "/tmp/key",
        "SSH_PORT": "22",
        "SSH_PASSWORD": "",
        "ADB_BINARY": "adb",
        "ADB_SERIAL": "",
        "ADB_WIFI_HOST": "",
        "ADB_WIFI_PORT": "5555",
        "MCU_DEBUG_ENABLED": "false",
        "PROBE_TYPE": "stlink",
        "TARGET_CHIP": "stm32f4",
        "PROBE_RS_BINARY": "probe-rs",
        "GDB_BINARY": "arm-none-eabi-gdb",
        "TIMEOUT": "15",
        "AUDIT_LOG": "/tmp/audit.log",
        "SERVER_NAME": "test-server",
    }
    base.update(kwargs)
    return base


def test_defaults():
    with mock.patch.dict(os.environ, make_env(), clear=True):
        s = Settings.from_env()
        assert s.transport == "ssh"
        assert s.ssh_host == "10.0.0.1"
        assert s.ssh_user == "root"
        assert s.server_name == "test-server"
        assert s.default_timeout == 15.0


def test_transport_validation():
    with mock.patch.dict(os.environ, make_env(TRANSPORT="xxx"), clear=True):
        with pytest.raises(ValueError, match="TRANSPORT"):
            Settings.from_env()


def test_transport_adb_usb():
    env = make_env(TRANSPORT="adb-usb", ADB_SERIAL="abc123")
    with mock.patch.dict(os.environ, env, clear=True):
        s = Settings.from_env()
        assert s.transport == "adb-usb"
        assert s.adb_serial == "abc123"


def test_transport_adb_wifi():
    env = make_env(TRANSPORT="adb-wifi", ADB_WIFI_HOST="10.0.0.5")
    with mock.patch.dict(os.environ, env, clear=True):
        s = Settings.from_env()
        assert s.transport == "adb-wifi"
        assert s.adb_wifi_host == "10.0.0.5"


def test_mcu_default_disabled():
    with mock.patch.dict(os.environ, make_env(), clear=True):
        s = Settings.from_env()
        assert s.mcu_debug_enabled is False


def test_mcu_enabled():
    env = make_env(MCU_DEBUG_ENABLED="true", PROBE_TYPE="jlink", TARGET_CHIP="stm32h743")
    with mock.patch.dict(os.environ, env, clear=True):
        s = Settings.from_env()
        assert s.mcu_debug_enabled is True
        assert s.probe_type == "jlink"
        assert s.target_chip == "stm32h743"


def test_mcu_enabled_true_values():
    for val in ("true", "1", "yes"):
        env = make_env(MCU_DEBUG_ENABLED=val)
        with mock.patch.dict(os.environ, env, clear=True):
            s = Settings.from_env()
            assert s.mcu_debug_enabled is True


def test_mcu_probe_type_i_jet():
    env = make_env(MCU_DEBUG_ENABLED="true", PROBE_TYPE="i-jet")
    with mock.patch.dict(os.environ, env, clear=True):
        s = Settings.from_env()
        assert s.probe_type == "i-jet"


def test_mcu_probe_type_invalid_fallback():
    env = make_env(MCU_DEBUG_ENABLED="true", PROBE_TYPE="unknown")
    with mock.patch.dict(os.environ, env, clear=True):
        s = Settings.from_env()
        assert s.probe_type == "stlink"


def test_extra_shell_prefixes():
    env = make_env(EXTRA_SHELL_PREFIXES="custom-tool,my-cmd")
    with mock.patch.dict(os.environ, env, clear=True):
        s = Settings.from_env()
        assert "custom-tool" in s.extra_prefixes
        assert "my-cmd" in s.extra_prefixes


def test_ratelimit_log_path_default():
    with mock.patch.dict(os.environ, make_env(), clear=True):
        s = Settings.from_env()
        assert str(s.audit_log_path) == "/tmp/audit.log"


def test_timeout_custom():
    env = make_env(TIMEOUT="60")
    with mock.patch.dict(os.environ, env, clear=True):
        s = Settings.from_env()
        assert s.default_timeout == 60.0