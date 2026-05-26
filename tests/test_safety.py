"""Tests for safety module."""

from __future__ import annotations

import pytest

from embedded_dev_mcp.safety import (
    check_shell_command,
    check_path,
    READ_PATH_ROOTS,
    quote,
)


def test_check_shell_prefix_allowed():
    ok, reason = check_shell_command("uname -a")
    assert ok is True


def test_check_shell_prefix_denied_rm():
    ok, reason = check_shell_command("rm -rf /tmp/test")
    assert ok is False
    assert "deny" in reason or "denied" in reason


def test_check_shell_prefix_unknown():
    ok, reason = check_shell_command("random-command")
    assert ok is False
    assert "no allow-list" in reason or "not allowed" in reason


def test_check_shell_prefix_extra():
    ok, reason = check_shell_command(
        "custom-tool --info",
        extra_allowed_prefixes=("custom-tool",),
    )
    assert ok is True


def test_check_path_allowed():
    ok, reason = check_path("/proc/cpuinfo", READ_PATH_ROOTS)
    assert ok is True


def test_check_path_denied():
    ok, reason = check_path("/root/.bashrc", READ_PATH_ROOTS)
    assert ok is False


def test_check_path_relative():
    ok, reason = check_path("relative/path", READ_PATH_ROOTS)
    assert ok is False
    assert "absolute" in reason


def test_quote_simple():
    assert quote("simple") == "simple"


def test_quote_space():
    assert quote("has space") == "'has space'"