"""MCU build tools — IAR, CMake, Makefile build support."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from ..audit import AuditLog


class McuBuildTools:
    """MCU firmware build tools."""

    def __init__(
        self,
        audit: AuditLog,
        iar_binary: str = "iarbuild",
        timeout: float = 120.0,
    ) -> None:
        self.audit = audit
        self.iar_binary = iar_binary
        self.timeout = timeout

    async def _run(self, operation: str, args: dict, result: str, ok: bool = True) -> str:
        self.audit.write(operation, args, result[:200], ok=ok)
        return result

    async def _exec(
        self, argv: list[str], timeout: float | None = None
    ) -> tuple[str, str, int]:
        """Execute a build command."""
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
                proc.returncode if proc.returncode is not None else -1,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "", f"Build timed out after {to}s", -1
        except FileNotFoundError:
            return "", f"Binary not found: {argv[0]}", -1

    async def iar_build(
        self, project_path: str, configuration: str = "Debug", clean_first: bool = False
    ) -> str:
        """Build an IAR EWARM project."""
        path = Path(project_path)
        if not path.exists():
            return await self._run(
                "iar_build", {"project": project_path},
                f"Project not found: {project_path}", ok=False,
            )
        if not project_path.endswith(".ewp"):
            return await self._run(
                "iar_build", {"project": project_path},
                "Project must be a .ewp file", ok=False,
            )

        args = [self.iar_binary, project_path]
        if clean_first:
            args.append("-clean")
        args.extend([configuration, "-log", "info"])

        stdout, stderr, rc = await self._exec(args, timeout=self.timeout)

        if rc != 0:
            errors = self._parse_iar_errors(stdout + stderr)
            return await self._run(
                "iar_build",
                {"project": project_path, "config": configuration},
                f"Build FAILED (rc={rc})\nErrors:\n{errors}",
                ok=False,
            )

        summary = self._parse_iar_summary(stdout)
        return await self._run(
            "iar_build",
            {"project": project_path, "config": configuration, "clean": clean_first},
            f"Build OK\n{summary}",
        )

    async def iar_clean(self, project_path: str, configuration: str = "Debug") -> str:
        """Clean an IAR EWARM project."""
        return await self.iar_build(project_path, configuration, clean_first=True)

    def _parse_iar_errors(self, output: str) -> str:
        """Extract error lines from IAR build output."""
        lines = output.splitlines()
        errors = [l for l in lines if "Error[" in l or "Fatal error[" in l]
        return "\n".join(errors[:20]) if errors else "(no error lines detected)"

    def _parse_iar_summary(self, output: str) -> str:
        """Extract build summary from IAR output."""
        lines = output.splitlines()
        summary_lines = []
        for line in lines:
            if any(k in line for k in (
                "bytes of", "Error(s)", "Warning(s)", "Total number",
                "Linking", "Updating",
            )):
                summary_lines.append(line.strip())
        return "\n".join(summary_lines) if summary_lines else output[-500:]