"""Append-only audit log for tool invocations."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AuditLog:
    """Audit logger that writes JSON lines to file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._prepared = False

    def _prepare(self) -> None:
        if self._prepared:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prepared = True

    def write(
        self,
        tool: str,
        args: dict[str, Any],
        result_summary: str,
        *,
        rc: int | None = None,
        ok: bool = True,
    ) -> None:
        """Write an audit entry."""
        try:
            self._prepare()
            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "tool": tool,
                "args": {k: _truncate(v) for k, v in args.items()},
                "ok": ok,
                "rc": rc,
                "result": result_summary[:400],
            }
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass


def _truncate(v: Any, limit: int = 200) -> Any:
    """Truncate string values for audit log."""
    if isinstance(v, str) and len(v) > limit:
        return v[:limit] + f"...<+{len(v) - limit}>"
    return v
