"""Tests for probe_manager module (mocked CLI)."""

from __future__ import annotations

import asyncio
import json
import os
from unittest import mock

import pytest

from embedded_dev_mcp.probe_manager import (
    PROBE_MAPPING,
    ProbeError,
    ProbeInfo,
    ProbeRsManager,
)


class FakeProc:
    """Fake subprocess for mocking probe-rs calls."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self._stdout = stdout.encode() if isinstance(stdout, str) else stdout
        self._stderr = stderr.encode() if isinstance(stderr, str) else stderr
        self.returncode = returncode
        self._killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self._killed = True

    async def wait(self):
        pass


async def fake_subprocess(*args, **kwargs):
    cmd = " ".join(args[0]) if args else ""
    if "list" in cmd:
        return FakeProc(
            stdout="0: ST-Link V2 (CMSIS-DAP) Serial: 12345ABCDEF\n"
                   "1: J-Link (J-Link) Serial: 987654321\n"
        )
    return FakeProc(stdout="ok\n", returncode=0)


@pytest.fixture
def manager():
    return ProbeRsManager(probe_type="stlink", target_chip="stm32f4")


def test_probe_mapping():
    assert PROBE_MAPPING["i-jet"] == "cmsisdap"
    assert PROBE_MAPPING["stlink"] == "stlink"
    assert PROBE_MAPPING["jlink"] == "jlink"


def test_manager_defaults():
    m = ProbeRsManager()
    assert m.probe_type == "stlink"
    assert m.target_chip == "stm32f4"
    assert m.probe_rs_binary == "probe-rs"
    assert m.gdb_binary == "arm-none-eabi-gdb"
    assert m.gdb_port == 1337
    assert m.timeout == 30.0


def test_manager_i_jet_mapping():
    m = ProbeRsManager(probe_type="i-jet")
    assert m.probe_type == "i-jet"
    assert m._probe_rs_type == "cmsisdap"


def test_manager_custom_gdb():
    m = ProbeRsManager(gdb_binary="gdb-multiarch", gdb_port=2331)
    assert m.gdb_binary == "gdb-multiarch"
    assert m.gdb_port == 2331


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_run_probe_rs(mock_exec):
    mock_exec.return_value = FakeProc(stdout="output\n", returncode=0)
    m = ProbeRsManager()
    stdout, stderr, rc = await m._run_probe_rs(["list"])
    assert rc == 0
    assert "output" in stdout


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_run_probe_rs_timeout(mock_exec):
    async def slow_communicate():
        await asyncio.sleep(99)
    proc = FakeProc()
    proc.communicate = slow_communicate
    mock_exec.return_value = proc
    m = ProbeRsManager(timeout=0.01)
    with pytest.raises(ProbeError, match="timed out"):
        await m._run_probe_rs(["list"])


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_list_probes(mock_exec):
    mock_exec.return_value = FakeProc(
        stdout="0: ST-Link V2 (ARM) Serial: ABC\n1: J-Link (SEGGER) Serial: XYZ\n",
    )
    m = ProbeRsManager()
    probes = await m.list_probes()
    assert len(probes) == 2
    assert probes[0].vendor == "ST-Link V2"
    assert probes[1].serial == "XYZ"


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_list_probes_empty(mock_exec):
    mock_exec.return_value = FakeProc(stdout="No probes found.\n", returncode=0)
    m = ProbeRsManager()
    probes = await m.list_probes()
    assert len(probes) == 0


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_erase_flash(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.erase_flash()
    assert "erased" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_erase_flash_failure(mock_exec):
    mock_exec.return_value = FakeProc(stderr="chip not found", returncode=1)
    m = ProbeRsManager()
    with pytest.raises(ProbeError, match="erase failed"):
        await m.erase_flash()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_program_flash(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.program_flash("/tmp/test.elf")
    assert "programmed" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_verify_flash(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.verify_flash("/tmp/test.elf")
    assert "verified" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_halt(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.halt()
    assert "halted" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_reset(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.reset()
    assert "reset" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_reset_with_halt(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.reset(halt=True)
    assert "reset" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_run(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.run()
    assert "running" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_step(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.step()
    assert "step" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_info(mock_exec):
    mock_exec.return_value = FakeProc(stdout="Chip: STM32F407VG\n", returncode=0)
    m = ProbeRsManager()
    result = await m.info()
    assert "STM32F407" in result


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_read_memory(mock_exec):
    mock_exec.return_value = FakeProc(stdout="DE AD BE EF\n", returncode=0)
    m = ProbeRsManager()
    result = await m.read_memory(0x08000000, 16)
    assert "DE" in result


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_write_memory(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.write_memory(0x20000000, "DEADBEEF")
    assert "Wrote" in result


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_set_breakpoint(mock_exec):
    mock_exec.return_value = FakeProc(
        stdout="Breakpoint 1 at 0x08000100\n", returncode=0,
    )
    m = ProbeRsManager()
    result = await m.set_breakpoint(0x08000100)
    assert "Breakpoint" in result


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_list_breakpoints_empty(mock_exec):
    mock_exec.return_value = FakeProc(stdout="No breakpoints\n", returncode=0)
    m = ProbeRsManager()
    result = await m.list_breakpoints()
    assert "No breakpoints" in result


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_clear_all_breakpoints(mock_exec):
    mock_exec.return_value = FakeProc(returncode=0)
    m = ProbeRsManager()
    result = await m.clear_all_breakpoints()
    assert "cleared" in result.lower()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_erase_flash_failure(mock_exec):
    mock_exec.return_value = FakeProc(stderr="chip not found", returncode=1)
    m = ProbeRsManager()
    with pytest.raises(ProbeError, match="Erase failed"):
        await m.erase_flash()


@mock.patch("embedded_dev_mcp.probe_manager.asyncio.create_subprocess_exec")
async def test_program_nonexistent_file_fails(mock_exec):
    mock_exec.return_value = FakeProc(stderr="File not found", returncode=1)
    m = ProbeRsManager()
    with pytest.raises(ProbeError, match="Program failed"):
        await m.program_flash("/nonexistent.elf")